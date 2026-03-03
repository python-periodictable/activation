class FetchAPI {
    response_callback = null;
    url = null;

    initialize (response_callback, ready_callback=() => {}, url="/api/calculate") {
        this.response_callback = response_callback;
        this.url = url;
        ready_callback();
    }

    submit(data) {
        fetch(this.url, {
            method: "POST",
            body: JSON.stringify(data),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(json => this.response_callback(json))
        .catch(error => this.response_callback({'success':false,'detail':{'fetch error':error}}));
    }
}

const API = new FetchAPI();