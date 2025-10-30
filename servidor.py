from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
import mysql.connector
from decimal import Decimal
from datetime import date, datetime, timedelta

# --- Configuración de la Aplicación ---
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto'

# --- Configuración de Pusher ---
pusher_client = pusher.Pusher(
  app_id='2071029',
  key='b70b4a665d55d377411e',
  secret='6826ee089fd47856e21e',
  cluster='us2',
  ssl=True
)

# --- Configuración de la DB ---
db_config = {
    "host": "185.232.14.52",
    "database": "u760464709_23005283_bd",
    "user": "u760464709_23005283_usr",
    "password": "rnUxcf3P#a"
}

# =========================================================================
# RUTAS PARA SERVIR LAS PÁGINAS HTML (Login, Registro, Dashboard)
# =========================================================================

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/registro")
def registro():
    return render_template("registro.html")

@app.route("/dashboard")
def dashboard():
    if 'idUsuario' not in session:
        return redirect(url_for('login'))

    # --- LÓGICA DEL SALUDO DINÁMICO ---
    try:
        id_usuario_actual = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT username FROM usuarios WHERE idUsuario = %s", (id_usuario_actual,))
        usuario = cursor.fetchone()
        username = usuario['username'] if usuario else "Usuario"

        hora_actual = datetime.now().hour
        
        if 5 <= hora_actual < 12:
            saludo = "Buenos Días"
        elif 12 <= hora_actual < 20:
            saludo = "Buenas Tardes"
        else:
            saludo = "Buenas Noches"

        return render_template("dashboard.html", saludo=saludo, username=username)

    except mysql.connector.Error as err:
        return render_template("dashboard.html", saludo="Bienvenido", username="Usuario")
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# =========================================================================
# API PARA AUTENTICACIÓN
# =========================================================================

@app.route("/registrarUsuario", methods=["POST"])
def registrarUsuario():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()

        cursor.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (usuario,))
        if cursor.fetchone():
            return make_response(jsonify({"error": "El nombre de usuario ya está en uso."}), 409)

        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (usuario, password))
        con.commit()
        return make_response(jsonify({"status": "Usuario registrado exitosamente"}), 201)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, password))
        user_data = cursor.fetchone()
        
        if user_data:
            session['idUsuario'] = user_data['idUsuario']
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear()
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

# =========================================================================
# API PARA EL VITALOG DASHBOARD
# =========================================================================

# --- API DE HÁBITOS ---

@app.route("/api/habitos", methods=["GET"])
def get_habitos():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_usuario = session['idUsuario']
        hoy = date.today().isoformat()
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        
        sql = """
            SELECT 
                h.idHabito, h.nombre, h.icono,
                (SELECT COUNT(1) FROM registros_habitos rh WHERE rh.idHabito = h.idHabito AND rh.fecha = %s) > 0 AS completadoHoy
            FROM habitos h
            WHERE h.idUsuario = %s
            ORDER BY h.idHabito
        """
        cursor.execute(sql, (hoy, id_usuario))
        habitos = cursor.fetchall()
        return jsonify(habitos)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/api/habito", methods=["POST"])
def add_habito():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_usuario = session['idUsuario']
        nombre = request.form.get("nombre")
        icono = request.form.get("icono", "bi-check-lg")
        
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        cursor.execute("INSERT INTO habitos (idUsuario, nombre, icono) VALUES (%s, %s, %s)", (id_usuario, nombre, icono))
        con.commit()
        return make_response(jsonify({"status": "Hábito creado"}), 201)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/api/habito/registrar", methods=["POST"])
def registrar_habito():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_habito = request.form.get("idHabito")
        fecha = request.form.get("fecha", date.today().isoformat())
        
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        
        cursor.execute("SELECT idRegistroHabito FROM registros_habitos WHERE idHabito = %s AND fecha = %s", (id_habito, fecha))
        existe = cursor.fetchone()
        
        if not existe:
            cursor.execute("INSERT INTO registros_habitos (idHabito, fecha) VALUES (%s, %s)", (id_habito, fecha))
            con.commit()
            return make_response(jsonify({"status": "Hábito registrado"}), 201)
        else:
            cursor.execute("DELETE FROM registros_habitos WHERE idHabito = %s AND fecha = %s", (id_habito, fecha))
            con.commit()
            return make_response(jsonify({"status": "Hábito des-registrado"}), 200)
            
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# --- API DE FITNESS ---

@app.route("/api/fitness", methods=["POST"])
def add_fitness():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_usuario = session['idUsuario']
        val = (
            id_usuario,
            request.form.get("fecha", date.today().isoformat()),
            request.form.get("descripcion"),
            request.form.get("tipo"),
            int(request.form.get("duracion_min", 0)),
            int(request.form.get("calorias", 0))
        )
        
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor()
        sql = "INSERT INTO registros_fitness (idUsuario, fecha, descripcion, tipo, duracion_min, calorias) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, val)
        con.commit()
        return make_response(jsonify({"status": "Ejercicio añadido"}), 201)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# --- API DE ANALÍTICAS (PARA LOS GRÁFICOS) ---

@app.route("/api/analytics/heatmap", methods=["GET"])
def get_heatmap_data():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_usuario = session['idUsuario']
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)

        sql = """
            SELECT 
                rh.fecha, 
                COUNT(rh.idHabito) AS total_completados
            FROM registros_habitos rh
            JOIN habitos h ON rh.idHabito = h.idHabito
            WHERE h.idUsuario = %s
            GROUP BY rh.fecha
            ORDER BY rh.fecha ASC
        """
        cursor.execute(sql, (id_usuario,))
        data = cursor.fetchall()
        
        heatmap_data = [{"x": r['fecha'].isoformat(), "y": r['total_completados']} for r in data]
        
        return jsonify(heatmap_data)
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

@app.route("/api/analytics/fitness_stats", methods=["GET"])
def get_fitness_stats():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "No autorizado"}), 401)
    try:
        id_usuario = session['idUsuario']
        fecha_hace_7_dias = (date.today() - timedelta(days=7)).isoformat()
        
        con = mysql.connector.connect(**db_config)
        cursor = con.cursor(dictionary=True)
        
        sql = """
            SELECT 
                SUM(duracion_min) AS total_minutos,
                SUM(calorias) AS total_calorias,
                COUNT(idFitness) AS total_sesiones
            FROM registros_fitness
            WHERE idUsuario = %s AND fecha >= %s
        """
        cursor.execute(sql, (id_usuario, fecha_hace_7_dias))
        stats = cursor.fetchone()
        
        stats['total_minutos'] = stats['total_minutos'] or 0
        stats['total_calorias'] = stats['total_calorias'] or 0
        stats['total_sesiones'] = stats['total_sesiones'] or 0

        sql_barras = """
            SELECT fecha, SUM(calorias) AS calorias_dia
            FROM registros_fitness
            WHERE idUsuario = %s AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """
        cursor.execute(sql_barras, (id_usuario, fecha_hace_7_dias))
        barras_data_db = cursor.fetchall()
        
        barras_labels = [r['fecha'].isoformat() for r in barras_data_db]
        barras_series = [int(r['calorias_dia']) for r in barras_data_db]

        return jsonify({
            "resumen": stats,
            "grafico_barras": {
                "labels": barras_labels,
                "series": barras_series
            }
        })
    except mysql.connector.Error as err:
        return make_response(jsonify({"error": f"Error de BD: {err}"}), 500)
    finally:
        if 'con' in locals() and con.is_connected():
            cursor.close()
            con.close()

# =========================================================================
# PUNTO DE ARRANQUE
# =========================================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)
