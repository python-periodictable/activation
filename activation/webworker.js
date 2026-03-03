// webworker.js

import { loadPyodide } from "./pyodide/pyodide.mjs";
// import { loadPyodide } from "./pyodide/pyodide.mjs";

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide();
  await self.pyodide.loadPackage(["numpy", "pytz", "micropip"]);

  // get the periodictable wheel name from the special file:
  const response = await fetch("./periodictable_wheel_name.txt");
  const wheelName = (await response.text()).trim();
  await self.pyodide.runPythonAsync(`
    import micropip
    await micropip.install("./${wheelName}")
    import periodictable
    print(periodictable.__version__)
  `)

  // Downloading a single file
  await pyodide.runPythonAsync(`
    from pyodide.http import pyfetch
    response = await pyfetch("./nact.py")
    with open("nact.py", "wb") as f:
        f.write(await response.bytes())
    import nact
    import json

  `)
}
let pyodideReadyPromise = loadPyodideAndPackages();
pyodideReadyPromise.then(() => self.postMessage({worker_ready: true}));

self.onmessage = async (event) => {
  // make sure loading is done
  await pyodideReadyPromise;
  // Now is the easy part, the one that is similar to working in the main thread:
  try {
    const json_data = JSON.stringify(event.data.data);
    let python = `
      request = json.loads('${json_data}')
      try:
          response = nact.api_call(request)
      except Exception:
          response = {
            'success': False,
            'version': periodictable.__version__,
            'detail': {'query': error()},
            'error': 'unexpected exception',
          }
      json.dumps(response)
    `;
    //console.log('python:', python);
    let results = await self.pyodide.runPythonAsync(python);
    let ldata = JSON.parse(results);
    self.postMessage(ldata);
  } catch (error) {
    self.postMessage({ success: false, detail: {error: error.message }});
  }
};