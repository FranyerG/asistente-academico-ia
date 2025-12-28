from flask import Flask, request, jsonify, render_template
import openai  # IMPORTANTE: Solo 'import openai', no 'from openai import OpenAI'
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configurar la API key desde variables de entorno
API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# Configurar OpenAI 0.28.0 para OpenRouter
openai.api_key = API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

# Headers adicionales para OpenRouter
import requests
openai.requestor = requests.Session()
openai.requestor.headers.update({
    "HTTP-Referer": "https://asistente-academico.onrender.com",
    "X-Title": "Asistente Académico IA"
})

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
        "openai_version": "0.28.0"
    })

@app.route('/test')
def test():
    """Endpoint de prueba simple"""
    try:
        # Prueba muy simple
        response = openai.ChatCompletion.create(
            model="google/gemma-7b-it:free",
            messages=[{"role": "user", "content": "Di 'Hola'"}],
            temperature=0.1,
            max_tokens=10
        )
        return jsonify({
            "status": "success",
            "response": response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        
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
                        "Responde siempre en español de manera amable y útil."
                    )
                }
            ]
        
        # Agregar mensaje del usuario
        sessions[session_id].append({
            "role": "user",
            "content": user_input
        })
        
        # Obtener respuesta de OpenRouter - SIEMPRE usar modelo gratuito primero
        try:
            response = openai.ChatCompletion.create(
                model="google/gemma-7b-it:free",  # Modelo GRATUITO
                messages=sessions[session_id],
                temperature=0.7,
                max_tokens=250
            )
            model_used = "gemma-7b-it (free)"
        except Exception as free_error:
            # Si falla, intentar con otro modelo
            print(f"Modelo gratuito falló: {free_error}")
            response = openai.ChatCompletion.create(
                model="meta-llama/llama-3-8b-instruct",
                messages=sessions[session_id],
                temperature=0.7,
                max_tokens=250
            )
            model_used = "llama-3-8b"
        
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
        # Error más amigable
        error_msg = str(e)
        if "401" in error_msg:
            return jsonify({'error': 'Error de autenticación. Verifica la API key.'}), 401
        elif "429" in error_msg:
            return jsonify({'error': 'Límite de solicitudes excedido. Intenta más tarde.'}), 429
        else:
            return jsonify({'error': 'Error en el servidor. Intenta nuevamente.'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
