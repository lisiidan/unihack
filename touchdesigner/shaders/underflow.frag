// UNDERFLOW / The Invisible City
// TouchDesigner GLSL TOP pixel shader; TD supplies #version and vUV.
// This is a procedural particle FIELD, not a persistent physics simulation.
// uState:  (time_seconds, air_severity, haze, wind)
// uPerson: (x, y, motion_strength, unused)
// Air conditions are visual interpretations, not calibrated measurements.
uniform vec4 uState;
uniform vec4 uPerson;
layout(location = 0) out vec4 fragColor;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

vec2 hash22(vec2 p) {
    return vec2(hash21(p + vec2(12.1, 44.7)),
                hash21(p + vec2(84.3, 27.4)));
}

void main() {
    vec2 uv = vUV.st;
    float t = uState.x;
    float air = clamp(uState.y, 0.0, 1.0);
    float haze = clamp(uState.z, 0.0, 1.0);
    float wind = clamp(uState.w, 0.0, 1.0);
    vec2 person = clamp(uPerson.xy, vec2(0.0), vec2(1.0));
    float movement = clamp(uPerson.z, 0.0, 1.0);
    vec2 scaleXY = vec2(uTDOutputInfo.res.z / max(uTDOutputInfo.res.w, 1.0), 1.0);

    // Deep cyan -> oxidized amber -> red as modeled pollution increases.
    vec3 clean = vec3(0.016, 0.075, 0.115);
    vec3 dirty = vec3(0.175, 0.045, 0.055);
    vec3 atmosphere = mix(clean, dirty, smoothstep(0.22, 0.9, air));
    float spatialNoise = sin(uv.x * 7.0 + t * 0.11)
                       * sin(uv.y * 9.0 - t * 0.08);
    vec3 col = atmosphere * (0.45 + 0.65 * uv.y)
             + haze * (0.017 + 0.018 * spatialNoise);

    // Atmospheric beams; a soft spatial composition rather than a dashboard.
    float beam = 0.0;
    for (int b = 0; b < 3; ++b) {
        float cx = 0.21 + float(b) * 0.32
                 + 0.055 * sin(t * (0.09 + float(b) * 0.028));
        float w = 0.04 + 0.03 * uv.y;
        beam += exp(-pow((uv.x - cx) / w, 2.0)) * smoothstep(0.2, 1.0, uv.y);
    }
    col += mix(vec3(0.02, 0.115, 0.14), vec3(0.16, 0.065, 0.05), air)
         * beam * (0.20 + haze * 0.45);

    // Stylized underside of a bridge, kept subtle for projection.
    float bridgeFloor = 0.925 - 0.040 * sin(uv.x * 6.2831853);
    float bridgeMask = smoothstep(bridgeFloor - 0.02, bridgeFloor + 0.004, uv.y);
    col = mix(col, vec3(0.009, 0.015, 0.022), bridgeMask * 0.92);

    // The river occupies the bottom quarter of the space.
    float waterMask = 1.0 - smoothstep(0.195, 0.24, uv.y);
    float wave = sin(uv.x * 54.0 + sin(uv.y * 32.0 + t * 0.55)
                     + t * (0.7 + wind * 0.8));
    wave += 0.5 * sin(uv.x * 104.0 - t * 0.66 + uv.y * 17.0);
    vec3 waterColor = mix(vec3(0.012, 0.070, 0.110),
                          vec3(0.20, 0.045, 0.047), air);
    waterColor += 0.05 * (0.5 + 0.5 * wave)
                * mix(vec3(0.20, 0.66, 0.70), vec3(0.95, 0.44, 0.31), air);
    col = mix(col, waterColor, waterMask);

    // GPU field of ~1800 individual dots. Local-neighbor reconstruction
    // avoids looping over EVERY particle for every screen pixel.
    vec2 gridSize = vec2(58.0, 32.0);
    vec2 gridUv = uv * gridSize;
    vec2 baseCell = floor(gridUv);
    float particles = 0.0;
    vec3 sparkleColor = vec3(0.0);

    for (int oy = -1; oy <= 1; ++oy) {
        for (int ox = -1; ox <= 1; ++ox) {
            vec2 id = baseCell + vec2(float(ox), float(oy));
            float r = hash21(id);
            // Haze increases density, not a representation of bio-particles.
            if (r > 0.30 + haze * 0.62)
                continue;

            vec2 center = (id + 0.17 + hash22(id) * 0.66) / gridSize;
            float drift = t * (0.45 + wind * 2.15);
            center += vec2(
                sin(drift * 0.55 + id.y * 1.73 + r * 19.0),
                cos(drift * 0.38 + id.x * 1.17 + r * 17.0)
            ) * (0.003 + wind * 0.008);

            // A visitor pushes nearby particles away; movement changes
            // the visual state without implying environmental data changes.
            vec2 away = (center - person) * scaleXY;
            float pd = length(away);
            float influence = movement * exp(-pd * pd / 0.042);
            center += normalize(center - person + vec2(0.00001))
                    * influence * (0.028 + 0.030 * wind);

            vec2 d = (uv - center) * scaleXY;
            float d2 = dot(d, d);
            float size = mix(0.000006, 0.000025, hash21(id + 71.0));
            float core = exp(-d2 / size);
            float halo = exp(-d2 / (size * 13.0));
            float pulse = 0.70 + 0.30 * sin(t * (1.0 + r * 3.0) + r * 10.0);
            particles += (core + 0.14 * halo) * pulse;
            sparkleColor += (core + 0.10 * halo) * pulse
                    * mix(vec3(0.43, 0.89, 0.86), vec3(0.95, 0.44, 0.32), air);
        }
    }
    col += sparkleColor * (0.55 + 0.35 * haze);

    // Visitor ripple propagates toward the river and dissolves into it.
    vec2 rel = (uv - person) * scaleXY;
    float distanceToPerson = length(rel);
    float radius = mod(t * 0.24, 0.47);
    float ring = exp(-pow((distanceToPerson - radius) * 85.0, 2.0));
    float nearPerson = exp(-distanceToPerson * distanceToPerson / 0.011);
    vec3 visitorColor = mix(vec3(0.24, 0.73, 0.74),
                            vec3(0.90, 0.43, 0.30), air);
    col += movement * visitorColor * (0.16 * ring + 0.11 * nearPerson);

    // Edge vignette keeps projected elements perceptible in a dark room.
    float edges = smoothstep(0.05, 0.36, uv.x)
                * (1.0 - smoothstep(0.67, 1.02, uv.x));
    col *= 0.66 + 0.34 * edges;
    col = col / (1.0 + col); // simple highlight roll-off
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
