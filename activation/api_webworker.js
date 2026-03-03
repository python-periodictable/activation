class WebWorkerAPI {
    response_callback = null;
    ready_callback = null;
    url = null;
    pyodideWorker = null;

    initialize (response_callback, ready_callback=() => {}, url="./webworker.js") {
        this.response_callback = response_callback;
        this.ready_callback = ready_callback;
        this.url = url;
        this.pyodideWorker = new Worker(this.url, {type: "module"});
        this.pyodideWorker.onmessage = (event) => {
            if ('worker_ready' in event.data) {
                this.ready_callback();
            }
            else {
                this.response_callback(event.data);
            }
        }
    }

    submit(data) {
        this.pyodideWorker.postMessage({
            data: data
        });
    }
}

const API = new WebWorkerAPI();
