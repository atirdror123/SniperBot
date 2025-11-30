import os
from flask import Flask, jsonify
import run_scanner
import sys
from io import StringIO

app = Flask(__name__)

@app.route('/scan', methods=['POST', 'GET'])
def trigger_scan():
    """
    Triggers the market scanner.
    """
    try:
        print("Received scan request. Starting scanner...")
        
        # Capture stdout to return as response (optional, but helpful for debugging)
        # old_stdout = sys.stdout
        # sys.stdout = mystdout = StringIO()
        
        # Run the scanner
        run_scanner.run_scanner()
        
        # sys.stdout = old_stdout
        # output = mystdout.getvalue()
        
        return jsonify({
            "status": "success", 
            "message": "Market scan completed successfully.",
            # "logs": output
        }), 200
        
    except Exception as e:
        print(f"Error during scan: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "Sniper Bot Scanner"}), 200

if __name__ == "__main__":
    # Use PORT environment variable if available (Cloud Run requirement)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
