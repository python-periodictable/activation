from pathlib import Path
import re
import sys
from flask import abort, Flask, request, jsonify, make_response, render_template, send_from_directory

# Import your refactored script (ensure it's named nact.py in the same folder)
sys.path.append(str(Path(__file__).parent / 'cgi-bin'))
import nact

app = Flask(__name__, template_folder="activation")


@app.route('/api/calculate', methods=['POST'])
def calculate():
    """
    Handles the API request, converts the input into a standard dict,
    and passes it to nact.cgi_call().
    """

    try:
        data = request.get_json()
        result = nact.api_call(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': 'Server error', 
            'detail': str(e)
        }), 500


@app.route('/')
@app.route('/index.html')
def serve_index():
    """
    Reads the index.html file, performs a regex substitution on a script tag,
    and returns the modified HTML.
    """
    return render_template(
        'index_template.html',
        api_script='api_fetch.js', 
        periodictable_version=nact.periodictable.__version__
    )


@app.route('/<path:filename>')
def serve_static_files(filename):
    """
    Serves any other file requested at the root level from the 'activation' folder.
    """
    # Prevent this route from accidentally serving the unmodified index.html
    if filename == 'index.html':
        # You can either call serve_index() directly or return a 404
        return serve_index()
    
    # Securely send the file from the 'activation' directory
    try:
        return send_from_directory('activation', filename)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        host, *rest = sys.argv[1].split(':', 1)
        port = int(rest[0]) if rest else 8008
    else:
        host, port = "localhost", 8008
        # Run the server in debug mode on port 5000
        app.run(debug=True, host=host, port=port)