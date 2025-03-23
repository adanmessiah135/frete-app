import os
import webbrowser
from app import app

# Abrir o navegador
webbrowser.open('http://localhost:5000')

# Iniciar o servidor Flask
app.run(host='0.0.0.0', port=5000)