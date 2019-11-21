activation
==========

Neutron activation calculator for the web.

This is a web interface to the
[periodictable](https://periodictable.readthedocs.io)
available on [github](https://github.com/pkienzle/periodictable).

[Live version](https://www.ncnr.nist.gov/resources/activation/)

Backend interface
=================

The backend service can be used directly for low volume traffic.  For high
volume, just install and use periodictable directly from Python.

To request a calculation, send a POST request with the following fields
to https://www.ncnr.nist.gov/cgi-bin/nact.py.  The fields are documented
in the [live version](https://www.ncnr.nist.gov/resources/activation).
The defaults for missing fields are indicated below.

Request fields
--------------

```javascript
request = {
    calculate: target, // target is "scattering" or "activation" or "all"
    sample: '',        // Material
    flux: '100000',    // Thermal flux
    Cd: '0',           // Cd ratio
    fast: '0',         // Thermal/fast ratio
    mass: '0',         // Mass
    exposure: '1',     // Time on beam
    rest: '[0,1,24,360]', // Time off beam
    density: '0',      // Density
    thickness: '1',    // Thickness
    wavelength: '1',   // Source neutrons
    xray: 'Cu Ka',     // Source Xrays
    decay: '0.001',    // target for "Time to decay below"
    abundance: 'IAEA'  // natural abundance tables (IAEA or NIST)
}
```

The response is a JSON object with the following fields
```javascript
response = {
    'success': True,
    'sample': {
        'name': sample,
        'formula': str(chem),
        'mass': mass,
        'density': chem.density,
        'thickness': thickness,
        'natural_density': chem.natural_density
    }
    'activation': {  // if calculate is 'activation' or 'all'
        'flux': fluence,
        'fast': fast_ratio,
        'Cd': Cd_ratio,
        'exposure': exposure,
        'rest': rest_times,
        'activity': [
            {
                'isotope': el.isotope, 'reaction': el.reaction,
                'product': el.daughter, 'halflife': el.Thalf_str,
                'comments': el.comments, 'levels': activity_el,
            }
            // ...
        ],
        rows,
        'total': total,
        'decay_level': decay_level,
        'decay_time': decay_time
    }
    'scattering': { // if calculate is 'scattering' or 'all'
        'neutron': {
            'wavelength': wavelength,
            'energy': nsf.neutron_energy(wavelength),
            'velocity': nsf.VELOCITY_FACTOR/wavelength
        },
        'xs': {'coh': xs[0], 'abs': xs[1], 'incoh': xs[2]},
        'sld': {'real': sld[0], 'imag': sld[1], 'incoh': sld[2]},
        'penetration': penetration,
        'transmission': 100*exp(-thickness/penetration)
    }
    'xray_scattering': { // if calculate is 'scattering' or 'all'
        'xray': {
            'wavelength': xray_wavelength,
            'energy': xsf.xray_energy(xray_wavelength)
        },
        'sld': {'real': xsld[0], 'imag': xsld[1]}
    }
}
```

and on failure:
```javascript
response = {
    'success': False,
    'error': 'unexpected exception',
    'detail':{'query': stack traceback}
}
```

Example
-------

```sh
    $ curl -d "sample=Co" -X POST https://www.ncnr.nist.gov/cgi-bin/nact.py
    {"sample": {"name": "Co", "density": 8.9000000000000004, "natural_density": 8.9000000000000004, "thickness": 1.0, "mass": 1.0, "formula": "Co"}, "activation": {"flux": 100000.0, "decay_level": 0.001, "total": [0.50882480946568631, 0.0097068430551489927, 1.5501977813400679e-05, 1.5423998799711213e-05], "rest": [0, 1, 24, 360], "activity": [{"reaction": "act", "product": "Co-60", "halflife": "5.272 y", "comments": "s for 10m isomer added to ground state", "levels": [1.550756280503848e-05, 1.5507330056885684e-05, 1.5501977813400642e-05, 1.5423998799711213e-05], "isotope": "Co-59"}, {"reaction": "act", "product": "Co-60m+", "halflife": "10.5 m", "comments": "", "levels": [0.50880930190288043, 0.009691335725091536, 2.6450954673146495e-42, 0.0], "isotope": "Co-59"}, {"reaction": "2n", "product": "Co-61", "halflife": "1.65 h", "comments": "Co-61 prod from Co-60m only", "levels": [7.3067671206463878e-16, 4.8004598780012441e-16, 3.0556749020075668e-20, 1.5291619557875176e-81], "isotope": "Co-59"}, {"reaction": "2n", "product": "Co-61", "halflife": "1.65 h", "comments": "Co-61 prod assuming all Co-60m has decayed to Co-60", "levels": [1.3649499897275873e-16, 8.9675605544492023e-17, 5.7081926346341585e-21, 2.8565705754412276e-82], "isotope": "Co-59"}], "exposure": 1.0, "decay_time": 1.5773675158317233, "fast": 0.0, "Cd": 0.0}, "scattering": {"sld": {"real": 2.2645416201426363, "imag": 0.0094030915024841538, "incoh": 5.6329882940161067}, "xs": {"coh": 0.070858102483180807, "abs": 1.8806183004968307, "incoh": 0.43843639843243204}, "penetration": 0.4184253079898973, "neutron": {"wavelength": 1.0, "energy": 81.804202355724115, "velocity": 3956.0339760560055}, "transmission": 9.163767420488476}, "xray_scattering": {"xray": {"wavelength": 1.5418000000000001, "energy": 8.0415220802373657}, "sld": {"real": 63.020248367719645, "imag": 9.1409737970421201}}, "success": true}
```
