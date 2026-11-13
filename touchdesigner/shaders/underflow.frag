// UNDERFLOW / The Invisible City — reactive light currents
// TouchDesigner GLSL TOP pixel shader. TD provides #version, vUV, uTDOutputInfo.
// uState: (elapsed_seconds, model_air_severity, haze, wind)
// uPerson: (motion_x, motion_y, smoothed_motion_energy, seconds_since_motion)
// Environmental data shapes the ambient artwork, NOT measured conditions at the bridge.
uniform vec4 uState;
uniform vec4 uPerson;
layout(location = 0) out vec4 fragColor;

const float TAU = 6.28318530718;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

vec2 hash22(vec2 p) {
    return vec2(hash21(p + vec2(12.1, 44.7)),
                hash21(p + vec2(84.3, 27.4)));
}

float bell(float distance, float width) {
    float q = distance / max(width, 0.00001);
    return exp(-q * q);
}

void main() {
    vec2 uv = vUV.st;
    float t = uState.x;
    float air = clamp(uState.y, 0.0, 1.0);
    float haze = clamp(uState.z, 0.0, 1.0);
    float wind = clamp(uState.w, 0.0, 1.0);
    vec2 hand = clamp(uPerson.xy, vec2(0.0), vec2(1.0));
    float energy = clamp(uPerson.z, 0.0, 1.0);
    float sinceMotion = max(uPerson.w, 0.0);

    // Projection-space normalization: circular forces on wide outputs.
    vec2 aspect = vec2(uTDOutputInfo.res.z / max(uTDOutputInfo.res.w, 0.00001), 1.0);
    vec2 rel = (uv - hand) * aspect;
    float radius = length(rel);
    vec2 direction = rel / max(radius, 0.0001);
    vec2 tangent = vec2(-direction.y, direction.x);

    // Inverse-warp the *sampling coordinates*: particles flow as an entire
    // field instead of independently teleporting to a new cell.
    float bubble = energy * bell(radius, 0.27);
    float vortex = energy * bell(radius - 0.17, 0.22);
    vec2 fieldDisplacement = (direction * bubble * 0.095
                            + tangent * vortex * 0.070 * sin(t * 2.4)) / aspect;
    vec2 p = uv - fieldDisplacement;

    vec3 clean = vec3(0.018, 0.24, 0.31);
    vec3 dirty = vec3(0.79, 0.22, 0.27);
    vec3 primary = mix(clean, dirty, smoothstep(0.24, 0.83, air));
    vec3 secondary = mix(vec3(0.06, 0.69, 0.69),
                         vec3(1.0, 0.50, 0.25), air);
    vec3 background = mix(vec3(0.004, 0.018, 0.031),
                          vec3(0.052, 0.009, 0.030), air);
    vec3 col = background * (0.75 + 0.32 * uv.y);

    // Moving volumetric "river in the air". Layered glowing filaments.
    // The visitor bends the current and opens a visible pocket in the flow.
    float ribbons = 0.0;
    float mist = 0.0;
    for (int k = 0; k < 5; k++) {
        float fi = float(k);
        float baseY = 0.24 + fi * 0.117;
        float curve = 0.12 * sin(p.x * (4.8 + fi * 0.24)
                     + t * (0.26 + wind * 0.35) + fi * 1.57);
        curve += 0.038 * sin(p.x * 17.0 - t * 0.44 + fi * 2.31);
        float distanceToCurrent = abs(p.y - baseY - curve);
        ribbons += bell(distanceToCurrent, 0.007 + haze * 0.009) * (1.0 - fi * 0.095);
        mist += bell(distanceToCurrent, 0.055 + haze * 0.018) * (1.0 - fi * 0.11);
    }
    col += secondary * (0.105 * mist + 0.75 * ribbons);
    col += primary * (0.045 + haze * 0.075) * mist;

    // Lighting pillars give the bridge space depth even without a 3D mesh.
    float shaft = 0.0;
    for (int j = 0; j < 3; j++) {
        float fj = float(j);
        float x = 0.16 + 0.34 * fj + 0.038 * sin(t * 0.15 + fj * 2.7);
        shaft += bell(uv.x - x, 0.045 + 0.06 * uv.y)
               * smoothstep(0.13, 0.95, uv.y);
    }
    col += secondary * shaft * (0.09 + 0.12 * haze);

    // Sparkles: fixed random positions in CELL coordinates, inverse-warped
    // by p so they move coherently as the audience gestures.
    vec2 grid = vec2(42.0, 27.0);
    vec2 gridP = p * grid;
    vec2 cell = floor(gridP);
    vec3 sparks = vec3(0.0);
    for (int oy = -1; oy <= 1; ++oy) {
        for (int ox = -1; ox <= 1; ++ox) {
            vec2 id = cell + vec2(float(ox), float(oy));
            float seed = hash21(id);
            if (seed > 0.42 + haze * 0.35)
                continue;
            vec2 offset = 0.13 + 0.74 * hash22(id + 17.3);
            // Tiny oscillation within each cell avoids grid-neighbor popping.
            vec2 particle = (id + offset) / grid;
            particle += 0.003 * vec2(
                sin(t * (0.3 + wind) + seed * TAU * 3.0),
                cos(t * (0.25 + wind) + seed * TAU * 4.0)
            );
            vec2 d = (p - particle) * aspect;
            float distanceSquared = dot(d, d);
            float width = mix(0.000005, 0.000025, hash21(id + 71.0));
            float core = exp(-distanceSquared / width);
            float halo = exp(-distanceSquared / (width * 20.0));
            float flicker = 0.75 + 0.25 * sin(t * (1.4 + seed * 3.7) + seed * 19.0);
            vec3 tint = mix(secondary, vec3(0.86, 0.95, 0.96), seed * 0.5);
            sparks += tint * (0.92 * core + 0.19 * halo) * flicker;
        }
    }
    col += sparks * (0.65 + haze * 0.50);

    // Motion -> expanding luminous shockwaves + a temporary bright vortex.
    // Additional rings keep the energy readable on a projector.
    float pulseAge = min(sinceMotion, 4.0);
    float envelope = energy * (0.75 + 0.25 * exp(-pulseAge));
    float shockwave = bell(radius - (0.09 + 0.12 * pulseAge), 0.012 + pulseAge * 0.008);
    float secondWave = bell(radius - (0.045 + 0.08 * pulseAge), 0.014);
    float interference = 0.5 + 0.5 * sin(radius * 65.0 - t * 11.0);
    float vortexGlow = bell(radius - 0.11, 0.12) * interference;
    col += secondary * envelope * (1.30 * shockwave + 0.55 * secondWave + 0.27 * vortexGlow);
    col += primary * bubble * 0.23;

    // Reflections: flowing river light across the bottom of the image.
    float riverEdge = 0.18 + 0.015 * sin(uv.x * 11.0 + t * 0.2);
    float riverMask = 1.0 - smoothstep(riverEdge - 0.015, riverEdge + 0.028, uv.y);
    float waves = 0.5 + 0.5 * sin(uv.x * 58.0 + sin(uv.y * 35.0 + t)
                                  - t * (0.45 + wind));
    float waterLight = pow(waves, 5.0) * (0.25 + 0.75 * ribbons);
    vec3 water = mix(background * 1.25, primary * 0.19, waves);
    water += secondary * waterLight * 0.32;
    col = mix(col, water, riverMask * 0.9);

    // Bridge roof silhouette (top), radial projector-friendly falloff.
    float roofY = 0.92 - 0.045 * sin(uv.x * TAU);
    float roof = smoothstep(roofY - 0.025, roofY + 0.008, uv.y);
    col = mix(col, vec3(0.003, 0.006, 0.010), roof * 0.95);
    vec2 edge = abs(uv - 0.5) * 2.0;
    float vignette = 1.0 - 0.33 * smoothstep(0.45, 1.0, length(edge));
    col *= vignette;

    // Exposure and soft highlight roll-off.
    col = 1.0 - exp(-max(col, vec3(0.0)) * 1.4);
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
