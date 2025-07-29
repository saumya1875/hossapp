import streamlit as st
import mysql.connector
import bcrypt
import pandas as pd
import base64



hide_streamlit_cloud_elements = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    a[title="View source"] {display: none !important;}
    button[kind="icon"] {display: none !important;}
    </style>
"""
st.markdown(hide_streamlit_cloud_elements, unsafe_allow_html=True)
# --- BACKGROUND IMAGE FUNCTION ---
def set_bg_from_local(image_file):
    with open(image_file, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()
    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0.3)),
            url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            font-weight: bold !important;
            padding: 20px;
            margin: 5px;
        }}
        .stButton > button {{
            background-color: blue;
            color: white;
            padding: 12px 24px;
            margin: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
        .stButton > button:hover {{
            background-color: #45a049;
        }}
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
            padding: 10px;
            margin: 5px;
            border-radius: 5px;
            border: 1px solid black;
        }}
        label {{
            font-weight: bold;
            color: green;
        }}
        .stSelectbox > div > div > select {{
            padding: 10px;
            margin: 5px;
            border-radius: 5px;
            border: 1px solid #ccc;
        }}
        .stDataFrame {{
            background-color: lightblue;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }}
        .stSubheader {{
            font-size: 50px;
            color: #333;
            padding: 30px;
            background-color: blue;
            border-radius: 5px;
            margin-bottom: 15px;
        }}
        </style>
    """, unsafe_allow_html=True)

# Database connection
def connect_to_mysql():
    try:
        return mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            user=st.secrets["mysql"]["root"],
            password=st.secrets["mysql"]["root"],
            database=st.secrets["mysql"]["hospital_managementt"]
        )
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None

# --- PASSWORD HASHING ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- USER AUTH ---
def user_exists(username):
    conn = connect_to_mysql()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def register_user(username, password, role, specialty=None, doctor_name=None):
    if user_exists(username):
        st.error("Username already exists!")
        return False
    conn = connect_to_mysql()
    if not conn:
        st.error("DB connection failed")
        return False
    cursor = conn.cursor()
    hashed = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password, role, specialty) VALUES (%s,%s,%s,%s)", 
                       (username, hashed, role, specialty))
        user_id = cursor.lastrowid
        if role == "doctor":
            if not doctor_name or not specialty:
                st.error("Doctor name and specialty required")
                return False
            cursor.execute("INSERT INTO doctors (user_id, name, specialty) VALUES (%s,%s,%s)",
                           (user_id, doctor_name, specialty))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as e:
        st.error(f"DB Error: {e}")
        return False

def authenticate_user(username, password):
    conn = connect_to_mysql()
    if not conn:
        return False, None, None
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, role FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and check_password(user[1], password):
        return True, user[2], user[0]
    return False, None, None

# --- DOCTOR FUNCTIONS ---
def get_doctors():
    conn = connect_to_mysql()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, specialty FROM doctors")
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return doctors

def delete_doctor(doctor_id):
    conn = connect_to_mysql()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctors WHERE id=%s", (doctor_id,))
    conn.commit()
    cursor.close()
    conn.close()

# --- PATIENT FUNCTIONS ---
def add_patient(name, age, gender, address, doctor_id=None):
    conn = connect_to_mysql()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("INSERT INTO patients (name, age, gender, address, doctor_id) VALUES (%s,%s,%s,%s,%s)",
                   (name, age, gender, address, doctor_id))
    conn.commit()
    cursor.close()
    conn.close()

def delete_patient(patient_id):
    conn = connect_to_mysql()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE id=%s", (patient_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_patients(doctor_id=None):
    conn = connect_to_mysql()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor()
    if doctor_id:
        cursor.execute("""SELECT p.id, p.name, p.age, p.gender, p.address, d.name 
                          FROM patients p 
                          LEFT JOIN doctors d ON p.doctor_id = d.id 
                          WHERE doctor_id=%s""", (doctor_id,))
    else:
        cursor.execute("""SELECT p.id, p.name, p.age, p.gender, p.address, d.name 
                          FROM patients p 
                          LEFT JOIN doctors d ON p.doctor_id = d.id""")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    df = pd.DataFrame(rows, columns=["ID", "Name", "Age", "Gender", "Address", "Doctor"])
    return df

# --- USERS for admin ---
def get_all_users():
    conn = connect_to_mysql()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(users, columns=["ID", "Username", "Role"])

def delete_user(user_id):
    conn = connect_to_mysql()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

# --- MAIN APP ---
def main():
    set_bg_from_local("sa.jpg")  # Replace with your background image file path
    st.title("🏥 Hospital Management System")

    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.session_state.page = "Login"

    # Sidebar menu options
    if st.session_state.logged_in:
        if st.session_state.role == "admin":
            menu = ["Add Patient", "View Patients", "Admin Dashboard", "Logout"]
        elif st.session_state.role == "doctor":
            menu = [ "View Patients", "Doctor Dashboard", "Logout"]
        else:
            menu = ["Add Patient", "View Patients", "Logout"]
    else:
        menu = ["Login", "Register"]

    choice = st.sidebar.selectbox("Menu", menu, index=menu.index(st.session_state.page) if st.session_state.page in menu else 0)
    st.session_state.page = choice

    if choice == "Login":
        set_bg_from_local("mmm.jpg")
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            success, role, user_id = authenticate_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.user_id = user_id
                st.success(f"Welcome {username} ({role})")
                if role == "admin":
                    st.session_state.page = "Admin Dashboard"
                else:
                    st.session_state.page = "Add Patient"
                
            else:
                st.error("Invalid username or password")

    elif choice == "Register":
        set_bg_from_local("as.jpg")
        st.subheader("📝 Register New User")
        role = st.selectbox("Select Role", ["admin", "doctor"])
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        specialty = None
        doctor_name = None
        if role == "doctor":
            doctor_name = st.text_input("Doctor Full Name")
            specialty = st.text_input("Specialty")
        if st.button("Register"):
            if username and password:
                if register_user(username, password, role, specialty, doctor_name):
                    st.success("User registered successfully! Please login.")
                else:
                    st.error("Registration failed.")
            else:
                st.error("Please fill in all required fields.")

    elif choice == "Add Patient":
        set_bg_from_local("mmmm.jpg")
        st.subheader("➕ Add Patient")
        name = st.text_input("Patient Name")
        age = st.number_input("Age", min_value=0, max_value=150, step=1)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        address = st.text_area("Address")
        doctors = get_doctors()
        doctor_map = {f"{d[1]} ({d[2]})": d[0] for d in doctors}
        doctor_name_selected = st.selectbox("Assign Doctor (optional)", ["None"] + list(doctor_map.keys()))
        doctor_id = doctor_map.get(doctor_name_selected) if doctor_name_selected != "None" else None
        if st.button("Add Patient"):
            if name and age > 0 and gender and address:
                add_patient(name, age, gender, address, doctor_id)
                st.success(f"Patient {name} added successfully!")
            else:
                st.error("Please fill all fields")

    elif choice == "View Patients":
        set_bg_from_local("sa.jpg")
        st.subheader("👨‍👩‍👧‍👦 Patients List")
        if st.session_state.role == "doctor":
            # Show only patients assigned to this doctor
            conn = connect_to_mysql()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM doctors WHERE user_id=%s", (st.session_state.user_id,))
            doc = cursor.fetchone()
            cursor.close()
            conn.close()
            doctor_id = doc[0] if doc else None
            patients_df = get_patients(doctor_id)
        else:
            patients_df = get_patients()

        st.dataframe(patients_df)

        if st.session_state.role == "admin":
            delete_id = st.number_input("Enter Patient ID to Delete", min_value=0, step=1)
            if st.button("Delete Patient"):
                delete_patient(delete_id)
                st.success(f"Deleted patient with ID {delete_id}")
                st.rerun()

    elif choice == "Admin Dashboard":
        set_bg_from_local("a5.jpg")
        st.subheader("🛠️ Admin Dashboard")

        st.markdown("### Users")
        users_df = get_all_users()
        st.dataframe(users_df)
        del_user_id = st.number_input("Enter User ID to Delete", min_value=0, step=1, key="del_user")
        if st.button("Delete User"):
            delete_user(del_user_id)
            st.success(f"Deleted user with ID {del_user_id}")

        st.markdown("---")
        st.markdown("### Doctors")
        doctors = get_doctors()
        for d in doctors:
            st.write(f"ID: {d[0]} | Name: {d[1]} | Specialty: {d[2]}")
        del_doc_id = st.number_input("Enter Doctor ID to Delete", min_value=0, step=1, key="del_doc")
        if st.button("Delete Doctor"):
            delete_doctor(del_doc_id)
            st.success(f"Deleted doctor with ID {del_doc_id}")
            st.rerun()

    elif choice == "Doctor Dashboard":
        set_bg_from_local("a2.jpg")
        st.subheader("🩺 Doctor Dashboard")
        # Show doctor info and patients assigned to this doctor
        conn = connect_to_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, specialty FROM doctors WHERE user_id=%s", (st.session_state.user_id,))
        doc = cursor.fetchone()
        cursor.close()
        conn.close()
        if doc:
            st.write(f"Doctor Name: {doc[1]}")
            st.write(f"Specialty: {doc[2]}")
            patients_df = get_patients(doc[0])
            st.dataframe(patients_df)
        else:
            st.error("Doctor profile not found.")
            st.rerun()

    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.session_state.page = "Login"
        st.success("Logged out successfully!")
        st.rerun()
        

if __name__ == "__main__":
    main() 
