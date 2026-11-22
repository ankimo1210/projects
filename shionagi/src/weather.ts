import * as T from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { canvasTexture, random } from './materials';

const noise = `
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float grain(vec2 p){vec2 i=floor(p),u=fract(p);u=u*u*(3.-2.*u);return mix(mix(hash(i),hash(i+vec2(1,0)),u.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),u.x),u.y);}
`;

export function terminalFloor() {
  const aggregate = new T.TextureLoader().load(import.meta.env.BASE_URL + 'art/port-concrete.webp');
  aggregate.wrapS = aggregate.wrapT = T.RepeatWrapping;
  aggregate.anisotropy = 4;
  const reflector = new Reflector(new T.PlaneGeometry(17.1, 41.1), {
    textureWidth: 600,
    textureHeight: 338,
    clipBias: 0.003,
    multisample: 0,
    shader: {
      name: 'Wet terminal tiles',
      uniforms: {
        color: { value: null },
        tDiffuse: { value: null },
        textureMatrix: { value: null },
        clock: { value: 0 },
        aggregate: { value: aggregate },
      },
      vertexShader: `uniform mat4 textureMatrix; varying vec4 mirror;varying vec3 world;void main(){world=(modelMatrix*vec4(position,1.)).xyz;mirror=textureMatrix*vec4(position,1.);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
      fragmentShader:
        noise +
        `
      uniform sampler2D tDiffuse;uniform sampler2D aggregate;uniform float clock;varying vec4 mirror;varying vec3 world;
      void main(){
        vec2 p=world.xz;
        vec2 tiles=fract(p/vec2(1.45,1.12));vec2 seam=min(tiles,1.-tiles);
        float edge=min(seam.x,seam.y);float pixel=max(.002,fwidth(edge));
        bool inside=p.y>-31.2&&p.y<10.2&&p.x<8.2;
        float joint=(1.-smoothstep(.004-pixel,.006+pixel,edge))*float(inside||p.y<-250.);
        float fine=grain(p*110.);float salt=grain(p*8.);float pool=smoothstep(.22,.7,grain(p*.68)+.22*grain(p*2.1));
        vec2 uv=mirror.xy/mirror.w;
        vec2 wave=vec2(grain(p*vec2(16.,5.)+clock*.09)-.5,grain(p*vec2(25.,9.))-.5);
        uv+=wave*(.004+.008*(1.-pool));
        vec3 refl=(texture2D(tDiffuse,uv).rgb*.57+texture2D(tDiffuse,uv+vec2(.002,-.003)).rgb*.28+texture2D(tDiffuse,uv+vec2(-.006,.004)).rgb*.15);
        float chips=dot(texture2D(aggregate,p/2.85).rgb,vec3(.25,.55,.20));
        float n=(.37+1.20*chips)*(.72+.20*salt+.10*fine);
        vec3 base=(inside?vec3(.061,.075,.076):vec3(.035,.051,.054))*n*(1.-.40*joint);
        float fres=1.-max(0.,normalize(cameraPosition-world).y);
        vec3 col=base*(1.-pool*.48)+refl*(.075+pow(fres,2.)*.52+pool*.25)*(1.-joint*.47);
        gl_FragColor=vec4(col,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    },
  });
  reflector.rotation.x = -Math.PI / 2;
  reflector.position.set(-0.5, 0.016, -10.5);
  const m = reflector.material as T.ShaderMaterial;
  m.uniforms.aggregate.value = aggregate;
  return {
    object: reflector,
    update: (t: number) => {
      m.uniforms.clock.value = t;
    },
  };
}

let weatherTexture: T.DataTexture | undefined;

// Periodic cloud density and side lighting in RG, independent rain seeds in BA.
// Baking the noise keeps both outdoor surfaces inexpensive on software renderers.
function weatherPattern() {
  if (weatherTexture) return weatherTexture;
  const size = 256,
    rnd = random(148591);
  const field = (nx: number, ny: number) => {
    const grid = Float32Array.from({ length: nx * ny }, () => rnd());
    return (u: number, v: number) => {
      const x = (u - Math.floor(u)) * nx,
        y = (v - Math.floor(v)) * ny;
      const ix = Math.floor(x),
        iy = Math.floor(y),
        jx = (ix + 1) % nx,
        jy = (iy + 1) % ny;
      const fx = x - ix,
        fy = y - iy,
        s = fx * fx * (3 - 2 * fx),
        t = fy * fy * (3 - 2 * fy);
      const a = grid[iy * nx + ix] + (grid[iy * nx + jx] - grid[iy * nx + ix]) * s;
      const b = grid[jy * nx + ix] + (grid[jy * nx + jx] - grid[jy * nx + ix]) * s;
      return a + (b - a) * t;
    };
  };
  const warp = field(4, 5),
    broad = field(5, 8),
    bank = field(10, 16),
    fold = field(24, 32),
    wisps = field(56, 64);
  const height = new Float32Array(size * size),
    bytes = new Uint8Array(size * size * 4);
  for (let j = 0; j < size; j++)
    for (let i = 0; i < size; i++) {
      const u = i / size,
        v = j / size,
        x = u + 0.13 * warp(u, v),
        y = v + 0.1 * warp(u + 0.36, v + 0.61);
      height[j * size + i] =
        0.46 * broad(x, y) + 0.29 * bank(x + 0.15, y) + 0.17 * fold(x, y) + 0.08 * wisps(x, y);
    }
  for (let j = 0; j < size; j++)
    for (let i = 0; i < size; i++) {
      const k = j * size + i;
      const slope =
        height[((j + 2) % size) * size + ((i + 2) % size)] -
        height[((j + size - 2) % size) * size + ((i + size - 2) % size)];
      bytes[k * 4] = Math.round(height[k] * 255);
      bytes[k * 4 + 1] = Math.round(T.MathUtils.clamp(0.5 + slope * 2.8, 0, 1) * 255);
      bytes[k * 4 + 2] = Math.floor(rnd() * 256);
      bytes[k * 4 + 3] = Math.floor(rnd() * 256);
    }
  weatherTexture = new T.DataTexture(bytes, size, size);
  weatherTexture.name = 'Harbour weather field';
  weatherTexture.wrapS = weatherTexture.wrapT = T.RepeatWrapping;
  weatherTexture.magFilter = weatherTexture.minFilter = T.LinearFilter;
  weatherTexture.needsUpdate = true;
  return weatherTexture;
}

export function harborSky(scene: T.Scene) {
  const panorama = new T.TextureLoader().load(import.meta.env.BASE_URL + 'art/outer-harbor.webp');
  panorama.colorSpace = T.SRGBColorSpace;
  const sky = new T.Mesh(
    new T.SphereGeometry(1, 48, 24),
    new T.ShaderMaterial({
      name: 'Open harbour sky',
      side: T.BackSide,
      depthWrite: false,
      toneMapped: false,
      uniforms: { panorama: { value: panorama }, weatherField: { value: weatherPattern() } },
      vertexShader: `
      varying vec3 direction;
      void main(){
        direction=position;
        vec3 ray=mat3(viewMatrix)*mat3(modelMatrix)*position;
        vec4 clip=projectionMatrix*vec4(ray,1.);
        gl_Position=clip.xyww;
      }`,
      fragmentShader: `
      uniform sampler2D panorama,weatherField;varying vec3 direction;
      void main(){
        vec3 d=normalize(direction);
        float belt=smoothstep(-.182,-.065,d.y)*(1.-smoothstep(.24,.421,d.y));
        vec3 sky=vec3(.013,.032,.044);
        if(d.y>-.16&&belt<1.){
          vec2 overhead=d.xz/(.52+max(d.y,0.));
          vec2 clouds=texture2D(weatherField,overhead*vec2(.45,.36)+vec2(.37,.56)).rg;
          vec2 folds=texture2D(weatherField,overhead*vec2(1.09,.83)+vec2(.13,.27)).rg;
          float loft=smoothstep(.22,.77,.74*clouds.r+.26*folds.r);
          vec3 dome=mix(vec3(.005,.013,.020),vec3(.030,.064,.076),loft);
          dome+=vec3(.007,.013,.015)*(.62*clouds.g+.38*folds.g-.46);
          vec2 stormUv=clamp(vec2(.52,.856)+overhead*vec2(.19,.093),vec2(.02,.73),vec2(.98,.989));
          dome=mix(dome,texture2D(panorama,stormUv).rgb,.23);
          sky=mix(sky,dome,smoothstep(-.16,.23,d.y));
        }
        if(belt>0.){
          float v=clamp(.304+1.65*asin(clamp(d.y,-1.,1.)),.005,.995);
          float a=fract(atan(d.x,d.z)*.318309886);
          // The azimuth wraps twice. Continuous gradients keep the seam on the
          // same mip level as the surrounding skyline.
          vec3 dx=dFdx(d),dy=dFdy(d);
          float azimuthScale=.318309886/max(.01,dot(d.xz,d.xz));
          float elevationScale=1.65*inversesqrt(max(.01,1.-d.y*d.y));
          vec2 gx=vec2((d.z*dx.x-d.x*dx.z)*azimuthScale,dx.y*elevationScale);
          vec2 gy=vec2((d.z*dy.x-d.x*dy.z)*azimuthScale,dy.y*elevationScale);
          vec3 harbor=textureGrad(panorama,vec2(.058+.942*a,v),gx*vec2(.942,1.),gy*vec2(.942,1.)).rgb;
          if(a>.936){
            vec3 next=textureGrad(panorama,vec2((a-.936)*.90625,v),gx*vec2(.90625,1.),gy*vec2(.90625,1.)).rgb;
            harbor=mix(harbor,next,smoothstep(.936,1.,a));
          }
          sky=mix(sky,harbor*vec3(.88,.96,.97),belt);
        }
        gl_FragColor=vec4(sky,1.);
        #include <colorspace_fragment>
      }`,
    }),
  );
  // Clip-space far depth and a rotation-only view centre the dome for the main
  // camera and for the reflector's virtual camera, even below the horizon.
  sky.name = 'Harbour sky';
  sky.renderOrder = 1;
  sky.rotation.y = -0.72;
  sky.frustumCulled = false;
  scene.add(sky);
  return sky;
}

export function shoppingFlood(scene: T.Scene) {
  const geometry = new T.PlaneGeometry(18.4, 120, 4, 48);
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(-0.5, 0, -103);
  const points = geometry.getAttribute('position');
  for (let i = 0; i < points.count; i++) {
    const z = points.getZ(i),
      depth = T.MathUtils.smoothstep(-z, 43, 70) * T.MathUtils.smoothstep(z, -163, -145);
    points.setY(i, 0.035 + 0.095 * depth);
  }
  geometry.computeBoundingSphere();
  const steps = Array.from({ length: 5 }, () => new T.Vector4(0, 0, -100, 0));
  const mat = new T.ShaderMaterial({
    name: 'Shallow water on Shiomi Street',
    transparent: true,
    depthWrite: false,
    uniforms: { clock: { value: 0 }, weatherField: { value: weatherPattern() }, footsteps: { value: steps } },
    vertexShader: `
      varying vec3 world;
      void main(){
        world=(modelMatrix*vec4(position,1.)).xyz;
        gl_Position=projectionMatrix*viewMatrix*vec4(world,1.);
      }`,
    fragmentShader: `
      uniform float clock;
      uniform sampler2D weatherField;
      uniform vec4 footsteps[5];
      varying vec3 world;
      void main(){
        vec2 p=world.xz;
        float range=length(p-cameraPosition.xz);
        float nearWater=1.-smoothstep(8.,37.,range);
        float chop=texture2D(weatherField,p*vec2(.039,.048)+vec2(clock*.007,-clock*.004)).r;
        float edge=smoothstep(.01,.26,min(p.x+9.7,8.7-p.x));
        edge*=smoothstep(.08,2.35,min(-43.-p.y,p.y+163.)+(chop-.5)*1.6);
        float depth=clamp((world.y-.035)/.095,0.,1.);
        float fres=1.-clamp(normalize(cameraPosition-world).y,0.,1.);
        float a=sin(6.2*p.x+3.3*p.y+chop*6.8+clock*1.91);
        float b=sin(-3.4*p.x+9.7*p.y+3.8*chop+clock*2.34);
        float wind=pow(max(0.,a*.57+b*.43),3.)*smoothstep(.27,.69,chop)*nearWater;
        float rain=0.,wake=0.;
        if(range<23.){
          vec2 grid=mat2(.93,.368,-.368,.93)*p*1.64,cell=floor(grid);
          vec2 seed=texture2D(weatherField,(mod(cell,256.)+.5)/256.).ba;
          float time=fract(clock*(.48+.62*seed.x)+seed.y);
          vec2 centre=.27+.46*fract(seed*vec2(11.9,17.1));
          vec2 dv=fract(grid)-centre;
          float r=length(dv),aa=clamp(fwidth(r),.004,.085);
          float radius=.024+.30*time;
          float ring=1.-smoothstep(.005,.015+aa,abs(r-radius));
          float echo=1.-smoothstep(.003,.013+aa,abs(r+(.027+.028*time)-radius));
          float lit=.49+.43*dot(dv/max(r,.001),vec2(-.57,.82));
          rain=(ring+.38*echo)*lit*(.55+.45*seed.y)*(1.-smoothstep(.26,.93,time))*(1.-smoothstep(10.,23.,range));
          for(int i=0;i<5;i++){
            float age=clock-footsteps[i].z;
            if(age>=0.&&age<1.38&&footsteps[i].w>0.){
              vec2 delta=p-footsteps[i].xy;float d=length(delta);
              float pixel=clamp(fwidth(d),.002,.052);
              float spread=.07+.52*age;
              float crest=1.-smoothstep(.006,.021+pixel,abs(d-spread));
              float trail=1.-smoothstep(.005,.013+pixel,abs(d+.049+.065*age-spread));
              float light=.61+.32*dot(delta/max(d,.001),vec2(-.58,.81));
              wake=max(wake,(crest+.53*trail)*light*(1.-smoothstep(.16,1.38,age))*footsteps[i].w);
            }
          }
        }
        float sparkle=clamp(.23*wind+.60*rain+.78*wake,0.,1.);
        vec3 body=mix(vec3(.019,.048,.055),vec3(.044,.080,.090),fres*fres);
        vec3 col=mix(body,vec3(.23,.31,.30),sparkle);
        float alpha=(.11+.092*depth+.057*fres+.061*wind+.20*rain+.36*wake)*edge;
        gl_FragColor=vec4(col,clamp(alpha*(.64+.36*nearWater),0.,.70));
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const sheet = new T.Mesh(geometry, mat);
  sheet.name = 'Tidal water on Shiomi Street';
  sheet.renderOrder = 2;
  scene.add(sheet);
  let previousX = 0,
    previousZ = 0,
    previousTime = -1,
    travel = 0,
    cursor = 0,
    side = 1;
  return (t: number, px: number, pz: number, moving: boolean) => {
    mat.uniforms.clock.value = t;
    const dx = px - previousX,
      dz = pz - previousZ,
      distance = Math.hypot(dx, dz),
      dt = t - previousTime;
    const inStreet = px > -9.7 && px < 8.7 && pz < -43 && pz > -163;
    sheet.visible = Math.hypot(Math.max(-9.7 - px, 0, px - 8.7), Math.max(-163 - pz, 0, pz + 43)) < 64;
    if (previousTime < 0 || dt < 0 || distance > 3) {
      for (const stamp of steps) stamp.set(0, 0, -100, 0);
      travel = 0;
    } else if (moving && inStreet && dt > 0) {
      const speed = Math.min(distance / dt, 4),
        length = 0.54 + 0.081 * speed;
      travel += distance;
      if (travel >= length && distance > 0.0001) {
        // Offset to alternating boot soles along the actual movement direction.
        steps[cursor].set(
          px - ((side * dz) / distance) * 0.088,
          pz + ((side * dx) / distance) * 0.088,
          t,
          0.72 + 0.085 * speed,
        );
        cursor = (cursor + 1) % steps.length;
        side = -side;
        travel %= length;
      }
    } else travel = 0;
    previousX = px;
    previousZ = pz;
    previousTime = t;
  };
}

export function water(scene: T.Scene) {
  const mat = new T.ShaderMaterial({
    uniforms: { clock: { value: 0 } },
    vertexShader: `
    varying vec3 world;void main(){world=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:
      noise +
      `
    varying vec3 world;uniform float clock;
    void main(){vec2 p=world.xz;float far=length(p-cameraPosition.xz);
      float b=grain(p*vec2(1.8,9.)+vec2(clock*.32,clock*.5));
      float r=sin(p.y*10.+clock*2.+sin(p.x*1.8+clock*.5)*2.)*.5+.5;
      float spec=pow(b*r,2.3);
      float fade=exp(-far*.016);
      vec3 c=mix(vec3(.022,.061,.069),vec3(.018,.046,.055)+spec*vec3(.13,.28,.29),fade);
      gl_FragColor=vec4(c,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
  });
  const mesh = new T.Mesh(new T.PlaneGeometry(390, 540), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(0, -0.63, -135);
  scene.add(mesh);
  return (t: number) => {
    mat.uniforms.clock.value = t;
  };
}

export function rain(scene: T.Scene) {
  const count = 1750,
    verts = new Float32Array(count * 6),
    rnd = random(553306);
  for (let i = 0; i < count; i++) {
    const x = rnd() * 36,
      z = rnd() * 36,
      y = rnd() * 13,
      len = 0.16 + rnd() * 0.38;
    verts.set([x, y, z, x + 0.095 * len, y - len, z + 0.13 * len], i * 6);
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.BufferAttribute(verts, 3));
  // Each pair shares an anchor, so drops never stretch as they wrap through the volume.
  const anchor = new Float32Array(count * 6);
  for (let i = 0; i < count; i++)
    for (let j = 0; j < 2; j++) anchor.set(verts.subarray(i * 6, i * 6 + 3), i * 6 + j * 3);
  g.setAttribute('anchor', new T.BufferAttribute(anchor, 3));
  const m = new T.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { clock: { value: 0 }, eye: { value: new T.Vector3() } },
    vertexShader: `attribute vec3 anchor;uniform float clock;uniform vec3 eye;varying float intensity;
    void main(){
      vec3 span=vec3(36.,13.,36.);
      vec3 center=vec3(eye.x,6.,eye.z);
      vec3 v=mod(anchor+vec3(clock*1.1,-clock*11.,clock*1.4)-center+.5*span,span)-.5*span+center;
      bool indoors=v.x>-9.05&&v.x<8.55&&v.z<10.5&&v.z>-31.4&&v.y<4.69;
      float dist=length(v.xz-eye.xz);
      intensity=indoors?0.:(.2+.52*(1.-smoothstep(1.,19.,dist)));
      gl_Position=projectionMatrix*viewMatrix*vec4(v+position-anchor,1.);}`,
    fragmentShader: `varying float intensity;void main(){gl_FragColor=vec4(.58,.77,.78,intensity*.42);}`,
  });
  const l = new T.LineSegments(g, m);
  l.frustumCulled = false;
  l.renderOrder = 4;
  scene.add(l);
  return (t: number, eye: T.Vector3) => {
    m.uniforms.clock.value = t;
    m.uniforms.eye.value.copy(eye);
  };
}

export function glassMaterial() {
  const rand = random(639);
  const tex = canvasTexture(384, 256, (c) => {
    c.clearRect(0, 0, 384, 256);
    let grad = c.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0, 'rgba(166,195,179,.52)');
    grad.addColorStop(0.25, 'rgba(124,161,155,.12)');
    grad.addColorStop(0.74, 'rgba(91,126,123,.06)');
    grad.addColorStop(1, 'rgba(120,152,142,.48)');
    c.fillStyle = grad;
    c.fillRect(0, 0, 384, 256);
    for (let i = 0; i < 480; i++) {
      const x = rand() * 384,
        y = rand() * 256,
        h = rand() ** 3 * 110 + 1;
      grad = c.createLinearGradient(x, y, x, y + h);
      grad.addColorStop(0, 'rgba(167,200,190,.03)');
      grad.addColorStop(1, 'rgba(173,205,197,.32)');
      c.strokeStyle = grad;
      c.lineWidth = 0.5 + rand() * 1.1;
      c.beginPath();
      c.moveTo(x, y);
      c.bezierCurveTo(x + 2, y + h * 0.3, x - 2, y + h * 0.7, x + 0.5, y + h);
      c.stroke();
      c.fillStyle = 'rgba(190,214,210,.31)';
      c.fillRect(x, y + h, 1, 1.7);
    }
  });
  return new T.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0.56,
    depthWrite: false,
    side: T.DoubleSide,
    toneMapped: false,
  });
}
