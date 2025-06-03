from app import create_app
from flask import render_template
import logging
import traceback
import socket

app = create_app()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.errorhandler(500)
def internal_error(error):
    logger.error('Server Error: %s', str(error))
    logger.error('Traceback: %s', traceback.format_exc())
    return render_template('error.html', error=str(error), traceback=traceback.format_exc()), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error('Not Found Error: %s', str(error))
    return render_template('error.html', error=str(error)), 404

if __name__ == '__main__':
    # Bilgisayarınızın IP adresini göster
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\nUygulama şu adreslerden erişilebilir:")
    print(f"Local: http://localhost:5000")
    print(f"Network: http://{local_ip}:5000\n")
    
    # Uygulamayı başlat
    app.run(host='0.0.0.0', debug=True, port=5000) 