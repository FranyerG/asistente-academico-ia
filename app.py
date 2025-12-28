from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configurar la API key desde variables de entorno
API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# FORMA CORRECTA para OpenAI >= 1.0.0
# No pasar parámetros extra que no sean soportados
try:
    client = OpenAI(
        api_key=API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
except TypeError as e:
    # Si falla, intentar sin parámetros extra
    print(f"Error creando cliente: {e}")
    client = OpenAI(api_key=API_KEY)
    client.base_url = "https://openrouter.ai/api/v1"

# Memoria por sesión
sessions = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        "status": "ok", 
        "message": "Asistente Académico IA funcionando",
        "openai_version": "1.x"
    })

@app.route('/test-api')
def test_api():
    """Endpoint para probar la conexión con OpenRouter"""
    try:
        # Prueba simple con modelo gratuito
        response = client.chat.completions.create(
            model="google/gemma-7b-it:free",
            messages=[{"role": "user", "content": "Di 'hola' en español"}],
            temperature=0.1,
            max_tokens=10
        )
        return jsonify({
            "status": "success",
            "message": response.choices[0].message.content,
            "model": "google/gemma-7b-it:free"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "api_key_prefix": API_KEY[:20] + "..." if API_KEY else "None"
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        
        # Validación básica
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        user_input = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_input:
            return jsonify({'error': 'El mensaje no puede estar vacío'}), 400
        
        # Inicializar o recuperar memoria de la sesión
        if session_id not in sessions:
            sessions[session_id] = [
                {
                    "role": "system",
                    "content": (
                        "Eres un orientador académico y mentor para estudiantes. "
                        "Explicas de forma clara, motivadora y sencilla. "
                        "Ayudas con técnicas de estudio, organización del tiempo, "
                        "orientación vocacional, informática básica, programación y redes. "
                        "Nunca humillas ni juzgas. Motivas al estudiante. "
                        "Responde siempre en español."
                    )
                }
            ]
        
        # Agregar mensaje del usuario
        sessions[session_id].append({
            "role": "user",
            "content": user_input
        })
        
        # PRIMERO intentar con modelo gratuito
        try:
            response = client.chat.completions.create(
                model="google/gemma-7b-it:free",
                messages=sessions[session_id],
                temperature=0.6,
                max_tokens=300
            )
            model_used = "google/gemma-7b-it:free"
        except Exception as free_error:
            # Si falla el gratuito, intentar con el modelo pagado
            print(f"Modelo gratuito falló: {free_error}")
            response = client.chat.completions.create(
                model="meta-llama/llama-3-8b-instruct",
                messages=sessions[session_id],
                temperature=0.6,
                max_tokens=300
            )
            model_used = "meta-llama/llama-3-8b-instruct"
        
        ia_response = response.choices[0].message.content
        
        # Agregar respuesta al historial
        sessions[session_id].append({
            "role": "assistant",
            "content": ia_response
        })
        
        # Mantener solo los últimos 15 mensajes
        if len(sessions[session_id]) > 15:
            sessions[session_id] = [sessions[session_id][0]] + sessions[session_id][-14:]
        
        return jsonify({
            'response': ia_response,
            'session_id': session_id,
            'model': model_used
        })
        
    except Exception as e:
        print(f"Error en chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
