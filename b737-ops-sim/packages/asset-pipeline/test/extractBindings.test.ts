import { describe, expect, it } from 'vitest';
import { extractBindings, type XmlSource } from '../src/extractBindings.js';

const FILES: Record<string, string> = {
  'Models/cockpit.xml': `<?xml version="1.0"?>
<PropertyList>
 <path>cockpit.ac</path>
 <model>
  <path>pedestal.xml</path>
  <offsets><x-m>0.5</x-m><y-m>0</y-m><z-m>-0.2</z-m></offsets>
 </model>
 <model>
  <path>Aircraft/737-800YV/Models/yoke/yoke.xml</path>
  <offsets><x-m>1.0</x-m><y-m>-0.5</y-m><z-m>0.1</z-m><heading-deg>5</heading-deg></offsets>
 </model>
 <animation>
  <type>rotate</type>
  <object-name>quadone</object-name>
  <object-name>no1thrarm</object-name>
  <property>controls/engines/engine[0]/throttle</property>
  <factor>50</factor>
  <axis><x>0</x><y>1</y><z>0</z></axis>
  <center><x-m>1.2</x-m><y-m>0</y-m><z-m>-0.4</z-m></center>
 </animation>
 <animation>
  <type>rotate</type>
  <object-name>flaparm</object-name>
  <property>controls/flight/flaps</property>
  <interpolation>
   <entry><ind>0</ind><dep>0</dep></entry>
   <entry><ind>1</ind><dep>-52</dep></entry>
  </interpolation>
  <axis><x>0</x><y>1</y><z>0</z></axis>
  <center><x-m>1.3</x-m><y-m>0.1</y-m><z-m>-0.4</z-m></center>
 </animation>
 <animation>
  <type>rotate</type>
  <object-name>irrelevant</object-name>
  <property>sim/some/other</property>
  <axis><x>1</x><y>0</y><z>0</z></axis>
 </animation>
</PropertyList>`,
  'Models/pedestal.xml': `<?xml version="1.0"?>
<PropertyList>
 <path>pedestal.ac</path>
 <animation>
  <type>rotate</type>
  <object-name>parkbrake_1</object-name>
  <property>controls/gear/brake-parking</property>
  <factor>40</factor>
  <axis><x>1</x><y>0</y><z>0</z></axis>
  <center><x-m>0</x-m><y-m>0</y-m><z-m>0</z-m></center>
 </animation>
</PropertyList>`,
  'Models/yoke/yoke.xml': `<?xml version="1.0"?>
<PropertyList>
 <path>yoke.ac</path>
</PropertyList>`,
};

const source: XmlSource = {
  read: (p) => FILES[p] ?? null,
  exists: (p) => p in FILES || p.endsWith('.ac'),
};

describe('extractBindings', () => {
  it('collects assembly instances with offset chains', () => {
    const b = extractBindings('Models/cockpit.xml', source);
    const acs = b.instances.map((i) => i.ac).sort();
    expect(acs).toEqual(['Models/cockpit.ac', 'Models/pedestal.ac', 'Models/yoke/yoke.ac']);
    const pedestal = b.instances.find((i) => i.ac === 'Models/pedestal.ac')!;
    expect(pedestal.chain).toHaveLength(1);
    expect(pedestal.chain[0]!.t).toEqual([0.5, 0, -0.2]);
    const yoke = b.instances.find((i) => i.ac === 'Models/yoke/yoke.ac')!;
    expect(yoke.chain[0]!.rDeg).toEqual([0, 0, 5]);
  });

  it('extracts relevant rotate animations with axis/center/factor', () => {
    const b = extractBindings('Models/cockpit.xml', source);
    const throttle = b.animations.find((a) => a.fgProperty.includes('engine[0]/throttle'))!;
    expect(throttle.objects).toEqual(['quadone', 'no1thrarm']);
    expect(throttle.factor).toBe(50);
    expect(throttle.center).toEqual([1.2, 0, -0.4]);
    expect(throttle.axis).toEqual([0, 1, 0]);
  });

  it('captures interpolation tables', () => {
    const b = extractBindings('Models/cockpit.xml', source);
    const flaps = b.animations.find((a) => a.fgProperty === 'controls/flight/flaps')!;
    expect(flaps.table).toEqual([
      [0, 0],
      [1, -52],
    ]);
  });

  it('ignores irrelevant properties and collects from included XMLs', () => {
    const b = extractBindings('Models/cockpit.xml', source);
    expect(b.animations.some((a) => a.fgProperty === 'sim/some/other')).toBe(false);
    expect(b.animations.some((a) => a.objects.includes('parkbrake_1'))).toBe(true);
  });
});
