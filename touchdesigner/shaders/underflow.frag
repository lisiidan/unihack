// UNDERFLOW — TIMISOARA / BEGA / living city atlas.
// TouchDesigner GLSL TOP pixel shader (TouchDesigner supplies the GLSL header).
// IMPORTANT: the city blocks and Bega curves are ARTISTIC, not surveyed GIS.
// Data: uState=(time, air severity, PM haze, wind speed mapped);
//       uEnv=(rain mapped, packet fresh, unused, unused);
//       uPerson=(x, y, current movement energy, seconds since last motion);
//       uTrail0..2=(x, y, energy, age) for camera-activated light echoes.
uniform vec4 uState;
uniform vec4 uPerson;
uniform vec4 uEnv;
uniform vec4 uTrail0;
uniform vec4 uTrail1;
uniform vec4 uTrail2;
layout(location = 0) out vec4 fragColor;
const float PI2 = 6.28318530718;

float hash21(vec2 v) {
    v = fract(v * vec2(123.34, 345.45));
    v += dot(v, v + 34.345);
    return fract(v.x * v.y);
}
vec2 hash22(vec2 v) {
    return vec2(hash21(v + vec2(12.1, 44.7)),
                hash21(v + vec2(84.3, 27.4)));
}
float gauss(float d, float width) {
    float v = d / max(width, 0.00001);
    return exp(-v * v);
}
float riverY(float x) {
    // A clear, continuous canal band across the composition. NOT geography.
    return 0.415 + 0.096 * sin(x * 5.8 - 0.65)
                 + 0.032 * sin(x * 11.4 + 0.82)
                 + 0.075 * x;
}
float traceEcho(vec2 uv, vec4 pulse, vec2 aspect) {
    if (pulse.z <= 0.005 || pulse.w > 4.0) return 0.0;
    float age = max(pulse.w, 0.0);
    float r = length((uv - pulse.xy) * aspect);
    float fade = pulse.z * (1.0 - smoothstep(1.5, 4.0, age));
    float outer = gauss(r - 0.03 - age * 0.103, 0.006 + age * 0.005);
    float inner = gauss(r - 0.012 - age * 0.061, 0.011 + age * 0.004);
    return fade * (outer + 0.40 * inner);
}

void main() {
    vec2 uv = vUV.st;
    float t = uState.x;
    float air = clamp(uState.y, 0.0, 1.0);
    float haze = clamp(uState.z, 0.0, 1.0);
    float wind = clamp(uState.w, 0.0, 1.0);
    float rain = clamp(uEnv.x, 0.0, 1.0);
    float ar = uTDOutputInfo.res.z / max(uTDOutputInfo.res.w, 0.0001);
    vec2 aspect = vec2(ar, 1.0);
    vec2 hand = clamp(uPerson.xy, vec2(0.0), vec2(1.0));
    float energy = clamp(uPerson.z, 0.0, 1.0);
    float sinceMotion = max(uPerson.w, 0.0);

    // Stormy amber/pink when air quality worsens, clean cyan otherwise.
    vec3 ink = mix(vec3(0.003, 0.014, 0.029), vec3(0.034, 0.010, 0.027), air);
    vec3 cyan = mix(vec3(0.02, 0.71, 0.92), vec3(0.99, 0.43, 0.23),
                    smoothstep(0.22, 0.83, air));
    vec3 accent = mix(vec3(0.28, 0.98, 0.86), vec3(1.0, 0.74, 0.32), air);
    vec3 white = vec3(0.83, 0.97, 1.00);
    vec3 col = ink * (0.85 + 0.3 * uv.y);

    // Strong visual hierarchy: top data region is dark and uncluttered.
    float atlasArea = 1.0 - smoothstep(0.77, 0.89, uv.y);
    float headerRule = gauss(uv.y - 0.794, 0.00095);
    col += cyan * headerRule * 0.13;
    float sideRule = gauss(uv.x - 0.038, 0.00075) * atlasArea;
    col += cyan * sideRule * 0.095;

    // Aerial city geometry: irregular tilted blocks behind the canal.
    // These are generative graphics, NOT measured building footprints.
    vec2 city = vec2(uv.x * 29.0 + uv.y * 5.2,
                     uv.y * 16.0 - uv.x * 2.5);
    vec2 cid = floor(city);
    vec2 f = fract(city);
    float margin = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
    float cellId = hash21(cid);
    float banding = 0.7 + 0.3 * sin(uv.y * 90.0 + uv.x * 43.0);
    float buildings = smoothstep(0.031, 0.044, margin)
                    * (1.0 - smoothstep(0.26, 0.31, margin))
                    * step(0.16, cellId);
    float street = gauss(margin, 0.02);
    float cityDistance = abs(uv.y - riverY(uv.x));
    float cityZone = smoothstep(0.145, 0.25, cityDistance) * atlasArea;
    float mapFade = 0.7 + 0.30 * sin(uv.x * 7.0 + uv.y * 3.0);
    col += cyan * buildings * cityZone * 0.058 * mapFade * banding;
    col += white * street * cityZone * 0.016;
    float node = gauss(length((f - 0.5) * vec2(0.7, 1.0)), 0.11);
    col += accent * node * cityZone * step(0.95, cellId) * 0.27;

    // A river should read as a BODY, not a few identical squiggles.
    // Meandering center line with sharp shorelines, banks, and deep middle.
    float signedD = uv.y - riverY(uv.x);
    float d = abs(signedD);
    float riverMask = 1.0 - smoothstep(0.090, 0.113, d);
    float nearBank = gauss(d - 0.105, 0.007);
    float outerBank = gauss(d - 0.122, 0.033);
    float centerGlow = gauss(d, 0.071);
    vec3 water = vec3(0.006, 0.066, 0.098) + cyan * (0.09 + 0.14 * centerGlow);
    water = mix(water, water * vec3(0.62, 0.87, 1.07), 0.5);
    col += cyan * outerBank * 0.30;
    col = mix(col, water, riverMask * 0.97);
    col += accent * nearBank * 0.93;
    col += cyan * gauss(d - 0.110, 0.024) * 0.30;

    // Motion bends the streaming reflections continuously (not dot repulsion).
    vec2 diff = (uv - hand) * aspect;
    float r = length(diff);
    vec2 radial = diff / max(r, 0.0001);
    vec2 tangential = vec2(-radial.y, radial.x);
    float handField = energy * gauss(r, 0.245);
    vec2 p = uv - (radial * handField * 0.085
                    + tangential * energy * gauss(r - 0.13, 0.16)
                       * 0.045 * sin(t * 2.1)) / aspect;

    // Long laminar flow only INSIDE the river band.
    float flow = 0.0;
    float reflection = 0.0;
    for (int k = 0; k < 6; ++k) {
        float fk = float(k);
        float offset = (fk - 2.5) * 0.025;
        float wavy = 0.007 * sin(p.x * 25.0 - t * (0.7 + 1.4 * wind)
                            + fk * 2.2);
        float currentD = p.y - riverY(p.x) - offset - wavy;
        float streamLine = gauss(currentD, 0.0025 + 0.002 * haze);
        flow += streamLine * (0.4 + 0.6 * sin(t * 0.47 + fk));
        reflection += gauss(currentD, 0.017 + haze * 0.010);
    }
    col += riverMask * (accent * flow * 0.30 +
                       cyan * reflection * (0.035 + 0.035 * haze));

    // Bright tiny living current segments — individual sparks with depth.
    vec2 grid = vec2(46.0, 26.0);
    vec2 gp = p * grid;
    vec2 base = floor(gp);
    vec3 particles = vec3(0.0);
    for (int oy = -1; oy <= 1; ++oy) {
        for (int ox = -1; ox <= 1; ++ox) {
            vec2 id = base + vec2(float(ox), float(oy));
            float seed = hash21(id);
            if (seed > 0.45 + 0.30 * haze) continue;
            vec2 center = (id + 0.16 + 0.68 * hash22(id + vec2(9.2, 5.7))) / grid;
            float flowShift = (0.001 + wind * 0.003)
                    * sin(t * (0.45 + wind) + seed * PI2);
            center += vec2(flowShift, flowShift * 0.3);
            vec2 pp = (p - center) * aspect;
            float rr = dot(pp, pp);
            float size = mix(0.000003, 0.000013, hash21(id + vec2(71.0)));
            float core = exp(-rr / size);
            float halo = exp(-rr / (size * 14.0));
            float shimmer = 0.6 + 0.4 * sin(t * (1.1 + seed * 3.0) + seed * 20.0);
            float environmentMask = 0.28 + 0.7 * (1.0 - smoothstep(0.12, 0.30,
                                  abs(center.y - riverY(center.x))));
            particles += mix(cyan, white, seed * 0.64) * shimmer
                      * (0.78 * core + 0.13 * halo) * environmentMask;
        }
    }
    col += particles * atlasArea * (0.78 + haze * 0.38);

    // Three urban crossings = artistic markers, not surveyed bridges.
    for (int k = 0; k < 3; ++k) {
        float x = 0.215 + 0.300 * float(k);
        float cy = riverY(x);
        float dx = abs(uv.x - x);
        float dy = abs(uv.y - cy);
        float roadSpan = 1.0 - smoothstep(0.145, 0.164, dy);
        float crossing = gauss(dx, 0.0030) * roadSpan;
        float halo = gauss(dx, 0.019) * roadSpan * 0.18;
        float nodeTop = gauss(length((uv - vec2(x, cy + 0.144)) * aspect), 0.013);
        float nodeBottom = gauss(length((uv - vec2(x, cy - 0.144)) * aspect), 0.013);
        col += white * crossing * 0.80 + accent * halo * 0.38;
        col += accent * (nodeTop + nodeBottom) * 1.40;
    }

    // Atmospheric indicators: modeled PM haze and rain alter appearance.
    float pollutedMist = gauss(d - 0.18, 0.20) * (0.04 + 0.12 * haze);
    col += cyan * pollutedMist * atlasArea;
    float droplets = pow(0.5 + 0.5 * sin(uv.x * 250.0 +
              hash21(vec2(floor(uv.x * 94.0), 17.0)) * 30.0 + t * 0.72), 14.0);
    float rainTravel = 0.5 + 0.5 * sin(uv.y * 68.0 + t * 17.0);
    col += accent * rain * droplets * rainTravel * atlasArea * 0.35;
    float ripples = pow(0.5 + 0.5 * sin(uv.x * 95.0 - t * (1.4 + wind) +
                    13.0 * sin(uv.y * 23.0)), 8.0);
    col += accent * ripples * riverMask * (0.065 + rain * 0.19);

    // Physical action: persistent three moving rings + spatial bloom.
    float lightHistory = traceEcho(uv, uTrail0, aspect)
                       + traceEcho(uv, uTrail1, aspect)
                       + traceEcho(uv, uTrail2, aspect);
    float wake = energy * gauss(r, 0.16);
    col += accent * (lightHistory * 1.15 + wake * 0.45);
    col += white * riverMask * lightHistory * 0.50;
    float haloEnergy = energy * gauss(r - 0.11, 0.16);
    col += cyan * haloEnergy * 0.15 * (0.5 + 0.5 * sin(t * 3.0));

    // Technical ornamental markings: ticks and city locator.
    float leftMark = gauss(uv.x - 0.044, 0.0015) *
                     (1.0 - smoothstep(0.024, 0.028, abs(uv.y - 0.43)));
    col += accent * leftMark * 0.40;
    float horizontalRule = gauss(uv.y - 0.084, 0.0011) *
                           smoothstep(0.044, 0.065, uv.x) *
                           (1.0 - smoothstep(0.94, 0.96, uv.x));
    col += cyan * horizontalRule * 0.16;

    // Exposure, avoid flat washed-out laser look on projectors.
    float vignette = 1.0 - 0.37 * smoothstep(0.54, 1.06,
                          length((uv - 0.5) * vec2(1.3, 1.0)));
    col *= vignette;
    col = 1.0 - exp(-max(col, vec3(0.0)) * 1.70);
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
