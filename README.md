activation
==========

Neutron activation calculator for the web.

This is a web interface to the
[periodictable](https://periodictable.readthedocs.io)
available on [github](https://github.com/pkienzle/periodictable).

[Live version](https://www.ncnr.nist.gov/resources/activation/)


Installation
============

The activation web frontend is in the activation subdirectory.
The backend API is in the cgi-bin folder (nact.py)

Be sure the web server is configured to use python 3, with the periodictable
package updated to the latest version:

    sudo pip3 install periodictable --upgrade

Be sure that changes to the periodictable backend are noted at the end of the
help section in index.html in the repository. As well as informing users
of updates this will also set the last modification date on index.html.

For testing you can run the server from the repository:

    pip install flask
    python flask_server.py [host | host:port]

Additional files:

* endf/* was used to generate the graphs of thermal resonances. It is not
  needed unless you wish to update the graphs, for example, when new versions of
  the endf database are released.

* flask_server.py is used to run a test server for debugging the web application, or
  showing potential new features to users. See the help inside the file for
  details on running the server.

* cgi-bin/massfrac.py computes mass fractions for the elements in a compound. It
  is not yet used by the web frontend.

* cgi-bin/hello.py is a minimal test script for python cgi.

Pyodide implementation
======================
You can make a serverless install using pyodide to run the backend API. The `deploy_calculator.sh`
script will install to `/var/html/resources/activation/index.html`.

To test the pyodide version before deploying, install into a temporary directory:
```sh
TARGET_DIR=/tmp/pt bash deploy_calculator.sh
(cd /tmp/pt && python -m http.server)
```
You can then navigate to http://localhost:8000/index.html to view the application.


Backend interface
=================

The backend service can be used directly for low volume traffic.  For high
volume, just install and use periodictable directly from Python.

To request a calculation, send a POST request with the following fields
to https://www.ncnr.nist.gov/cgi-bin/nact.py.  The fields are documented
in the [live version](https://www.ncnr.nist.gov/resources/activation).
The defaults for missing fields are indicated below.  Note that the
"Time off beam" field on the input form is appended as the final value
for the *rest* field.  *decay* and *abundance* are not directly
controlled on the web form, but are instead set using data fields in
the web client url.

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

```python
python_request = {
    'calculate': "all", # target is "scattering" or "activation" or "all"
    'sample': 'Co',        # Material
    'flux': '100000',    # Thermal flux
    'Cd': '0',           # Cd ratio
    'fast': '0',         # Thermal/fast ratio
    'mass': '0',         # Mass
    'exposure': '1',     # Time on beam
    'rest': ["0","1","24","360"], # Time off beam
    'density': '0',      # Density
    'thickness': '1',    # Thickness
    'wavelength': '1',   # Source neutrons
    'xray': 'Cu Ka',     # Source Xrays
    'decay': '0.001',    # target for "Time to decay below"
    'abundance': 'IAEA'  # natural abundance tables (IAEA or NIST)
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
$ curl -s -d '{"sample": "Co"}' -H "Content-Type: application/json" -X POST http://localhost:8008/api/calculate | python -m json.tool
{
    "activation": {
        "Cd": 0.0,
        "activity": [
            {
                "comments": "",
                "halflife": "10.5 m",
                "isotope": "Co-59",
                "levels": [
                    0.5087467869376632,
                    0.009690144997026036,
                    2.6447704770864502e-42,
                    0.0
                ],
                "product": "Co-60m+",
                "reaction": "act"
            },
            {
                "comments": "Co-61 prod from Co-60m only",
                "halflife": "1.65 h",
                "isotope": "Co-59",
                "levels": [
                    7.305869373119584e-16,
                    4.799870068457319e-16,
                    3.0552994658480865e-20,
                    1.52897407497221e-81
                ],
                "product": "Co-61",
                "reaction": "2n"
            },
            {
                "comments": "s for 10m isomer added to ground state",
                "halflife": "5.272 y",
                "isotope": "Co-59",
                "levels": [
                    1.5505657464889658e-05,
                    1.5505424745333514e-05,
                    1.5500073159453058e-05,
                    1.5422103726672467e-05
                ],
                "product": "Co-60",
                "reaction": "act"
            },
            {
                "comments": "Co-61 prod assuming all Co-60m has decayed to Co-60",
                "halflife": "1.65 h",
                "isotope": "Co-59",
                "levels": [
                    1.3647822848511002e-16,
                    8.966458753177e-17,
                    5.707491296308241e-21,
                    2.8562196022780084e-82
                ],
                "product": "Co-61",
                "reaction": "2n"
            }
        ],
        "decay_level": 0.001,
        "decay_time": 1.5773360047132599,
        "exposure": 1.0,
        "fast": 0.0,
        "flux": 100000.0,
        "rest": [
            0,
            1,
            24,
            360
        ],
        "total": [
            0.508762292595129,
            0.00970565042177194,
            1.5500073159453095e-05,
            1.5422103726672467e-05
        ]
    },
    "sample": {
        "density": 8.9,
        "formula": "Co",
        "formula_latex": "Co",
        "mass": 1.0,
        "name": "Co",
        "natural_density": 8.9,
        "thickness": 1.0
    },
    "scattering": {
        "contrast_match": {
            "D2O_fraction": 0.4066002243307043,
            "sld": 2.2645414633790257
        },
        "neutron": {
            "energy": 81.80421023488275,
            "velocity": 3956.0340061039888,
            "wavelength": 1.0
        },
        "penetration": 0.4184253369555237,
        "sld": {
            "imag": 0.009403090851552168,
            "incoh": 5.632980055822083,
            "real": 2.2645414633790257
        },
        "transmission": 9.16376893656492,
        "xs": {
            "abs": 1.8806181703104334,
            "coh": 0.07085931929382916,
            "incoh": 0.4384351463657107
        }
    },
    "success": true,
    "version": "2.0.2",
    "xray_scattering": {
        "sld": {
            "imag": 9.140742563282087,
            "real": 63.02025244915057
        },
        "xray": {
            "energy": 8.041522793695698,
            "wavelength": 1.5418
        }
    }
}
```
