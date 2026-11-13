// UNDERFLOW / The Invisible City. TouchDesigner GLSL TOP fragment shader.
// Canalul Bega is a stylized ribbon, NOT a GIS-accurate river centerline.
// uState = (seconds, airSeverity, haze, wind)
// uPerson = (x, y, movement, secondsSinceMovement)
// uEnv = (rainNormalized, packetIsFresh, unused, unused)
// uTrail0..2 = (positionX, positionY, strength, ageSeconds)
uniform vec4 uState;
uniform vec4 uPerson;
uniform vec4 uEnv;
uniform vec4 uTrail0;
uniform vec4 uTrail1;
uniform vec4 uTrail2;
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
float bell(float x, float w) {
    float q = x / max(w, 0.0001);
    return exp(-q * q);
}
float begaCenter(float x) {
    // Artistic projection of the canal meandering through Timisoara.
    return 0.49 + 0.095 * sin(5.4 * x + 0.35)
                + 0.038 * sin(12.9 * x + 1.4) - 0.04 * x;
}
float trailRing(vec2 point, vec4 pulse, float aspectRatio) {
    if (pulse.z <= 0.0 || pulse.w >= 4.0) return 0.0;
    vec2 d = (point - pulse.xy) * vec2(aspectRatio, 1.0);
    float r = length(d);
    float age = max(pulse.w, 0.0);
    float fade = (1.0 - smoothstep(1.8, 4.0, age)) * pulse.z;
    return fade * (bell(r - 0.055 - age * 0.092, 0.009 + age * 0.007)
                  + 0.19 * bell(r - 0.022 - age * 0.052, 0.021));
}

void main() {
    vec2 uv = vUV.st;
    float t = uState.x;
    float air = clamp(uState.y, 0.0, 1.0);
    float haze = clamp(uState.z, 0.0, 1.0);
    float wind = clamp(uState.w, 0.0, 1.0);
    float rain = clamp(uEnv.x, 0.0, 1.0);
    vec2 person = clamp(uPerson.xy, vec2(0.0), vec2(1.0));
    float movement = clamp(uPerson.z, 0.0, 1.0);

    float aspectRatio = uTDOutputInfo.res.z / max(uTDOutputInfo.res.w, 1.0);
    vec2 aspect = vec2(aspectRatio, 1.0);
    vec2 rel = (uv - person) * aspect;
    float distanceToPerson = length(rel);
    vec2 away = rel / max(distanceToPerson, 0.0001);
    vec2 tangent = vec2(-away.y, away.x);
    float influence = movement * bell(distanceToPerson, 0.24);

    // Warp procedural light in a coherent field instead of teleporting dots.
    vec2 sampleUV = uv -
         (away * influence * 0.082 +
          tangent * movement * bell(distanceToPerson - 0.13, 0.17)
            * 0.042 * sin(t * 2.5)) / aspect;

    vec3 clean = vec3(0.015, 0.24, 0.30);
    vec3 dirty = vec3(0.76, 0.20, 0.22);
    vec3 mainColor = mix(clean, dirty, smoothstep(0.22, 0.85, air));
    vec3 glintColor = mix(vec3(0.13, 0.85, 0.80),
                          vec3(1.00, 0.49, 0.24), air);
    vec3 bg = mix(vec3(0.003, 0.014, 0.027),
                  vec3(0.047, 0.009, 0.028), air);
    vec3 col = bg * (0.85 + 0.34 * uv.y);

    // Canalul Bega: dominant luminous water ribbon with depth and banks.
    float signedRiver = uv.y - begaCenter(uv.x);
    float bankDistance = abs(signedRiver);
    float river = 1.0 - smoothstep(0.079, 0.122, bankDistance);
    float shoreline = bell(bankDistance - 0.098, 0.014);
    float riverAxis = bell(signedRiver, 0.041);

    float stream1 = sin(sampleUV.x * 64.0 + sin(sampleUV.y * 42.0 + t * 0.7)
                        - t * (1.3 + wind * 2.0));
    float stream2 = sin(sampleUV.x * 138.0 - t * (2.0 + wind * 1.5)
                        + sin(signedRiver * 65.0));
    float smallWaves = pow(0.5 + 0.5 * stream1, 5.0);
    float crossWaves = pow(0.5 + 0.5 * stream2, 9.0);
    vec3 riverBody = mainColor * (0.16 + 0.17 * riverAxis)
                   + bg * 0.52
                   + glintColor * (0.07 * smallWaves + 0.11 * crossWaves);
    col = mix(col, riverBody, river * 0.92);
    col += glintColor * shoreline * (0.24 + 0.12 * sin(t + uv.x * 19.0));
    col += mainColor * riverAxis * 0.12;

    // Concentric tracers follow the canal instead of appearing as random lines.
    float riverCurrents = 0.0;
    for (int k = 0; k < 4; ++k) {
        float fi = float(k);
        float offset = (fi - 1.5) * 0.039;
        float deviation = 0.011 * sin(uv.x * (20.0 + fi * 3.0)
                          - t * (0.52 + 0.24 * wind) + fi * 1.23);
        riverCurrents += bell(signedRiver - offset - deviation, 0.005 + 0.004 * haze);
    }
    col += glintColor * river * riverCurrents * 0.30;

    // Three abstract crossing signals — symbolic urban infrastructure.
    // These are NOT mapped to particular real bridges.
    float crossings = 0.0;
    for (int k = 0; k < 3; ++k) {
        float x = 0.19 + float(k) * 0.305;
        float xDist = abs(uv.x - x);
        float deck = bell(xDist, 0.0025) *
                     (1.0 - smoothstep(0.11, 0.14, bankDistance));
        float luminousNode = bell(length((uv - vec2(x, begaCenter(x))) * aspect), 0.018);
        crossings += 0.88 * deck + 0.55 * luminousNode;
    }
    col += mix(glintColor, vec3(0.82, 0.95, 1.0), 0.45) * crossings * 0.50;

    // Upper atmosphere: long currents drift across the city toward the river.
    float filaments = 0.0;
    float fog = 0.0;
    for (int k = 0; k < 5; ++k) {
        float fi = float(k);
        float curve = 0.17 + 0.14 * fi
              + 0.064 * sin(sampleUV.x * (6.0 + fi * 0.4)
                + t * (0.19 + wind * 0.28) + fi * 1.43)
              + 0.02 * sin(sampleUV.x * 16.0 - t * 0.42 + fi);
        float d = sampleUV.y - curve;
        filaments += bell(d, 0.004 + 0.007 * haze) * (0.85 - fi * 0.1);
        fog += bell(d, 0.060 + 0.04 * haze) * (0.8 - fi * 0.1);
    }
    col += glintColor * (0.35 * filaments + 0.05 * fog);
    col += mainColor * haze * fog * 0.060;

    // Fine dust uses consistent local cell positions and two-tone halos.
    vec2 grid = vec2(42.0, 27.0);
    vec2 g = sampleUV * grid;
    vec2 baseCell = floor(g);
    vec3 sparks = vec3(0.0);
    for (int oy = -1; oy <= 1; ++oy) {
        for (int ox = -1; ox <= 1; ++ox) {
            vec2 id = baseCell + vec2(float(ox), float(oy));
            float seed = hash21(id);
            if (seed > 0.39 + haze * 0.35) continue;
            vec2 particle = (id + 0.14 + hash22(id + 12.3) * 0.72) / grid;
            particle += 0.003 * vec2(
               sin(t * (0.3 + wind) + seed * 18.0),
               cos(t * (0.26 + wind) + seed * 25.0));
            vec2 d = (sampleUV - particle) * aspect;
            float d2 = dot(d, d);
            float size = mix(0.000004, 0.000018, hash21(id + 51.0));
            float core = exp(-d2 / size);
            float halo = exp(-d2 / (size * 17.0));
            float flicker = 0.75 + 0.25 * sin(t * (1.1 + seed * 3.0) + seed * 17.0);
            sparks += mix(glintColor, vec3(0.84, 0.96, 1.0), seed * 0.45)
                    * (core + halo * 0.17) * flicker;
        }
    }
    col += sparks * (0.55 + 0.45 * haze);

    // Rain uses actual precipitation from the packet when available.
    // Vertical glimmers + intensified ripples, no fabricated sensor values.
    float rainColumn = pow(0.5 + 0.5 *
                          sin(uv.x * 270.0 + hash21(floor(uv.x * 95.0)) * 25.0
                          + t * 1.2), 12.0);
    float fall = 0.5 + 0.5 * sin(uv.y * 45.0 + t * 11.0);
    col += glintColor * rain * rainColumn * fall * 0.18;
    col += glintColor * rain * river * smallWaves * 0.11;

    // Gesture history: three expanding rings remain after the hand moved.
    float trailing = trailRing(uv, uTrail0, aspectRatio)
                   + trailRing(uv, uTrail1, aspectRatio)
                   + trailRing(uv, uTrail2, aspectRatio);
    float nearPerson = bell(distanceToPerson, 0.12);
    col += glintColor * (1.1 * trailing + movement * nearPerson * 0.25);
    // A moving hand also disturbs Bega's surface near the gesture.
    col += glintColor * river * (0.22 * trailing + 0.09 * influence);

    // Slightly darken the top, suggesting bridge vault and projector vignette.
    float ceiling = smoothstep(0.915, 0.96, uv.y);
    col = mix(col, vec3(0.003, 0.005, 0.010), ceiling * 0.88);
    vec2 edge = abs(uv - 0.5) * 2.0;
    col *= 1.0 - 0.30 * smoothstep(0.52, 1.02, length(edge));
    col = 1.0 - exp(-max(col, vec3(0.0)) * 1.5);
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
