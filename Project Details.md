# Utility Bill Calculator Suite

## 📌 Project Overview

The Utility Bill Calculator Suite is a Python-based application that helps users calculate utility bills quickly and accurately. The system supports Electricity, Water, Gas, and Internet bill calculations. It includes separate login access for users and administrators. Users can calculate bills and view their calculation history, while administrators can monitor user activity and modify billing rates and default charges.

---

# 🎯 Problem Statement

Manual utility bill calculation is often time-consuming and prone to errors. Existing systems usually provide only bill calculation without maintaining user history or allowing administrators to manage billing rates. Therefore, there is a need for a simple, secure, and efficient utility billing system that enables users to calculate bills, view previous records, and allows administrators to manage billing information and monitor user activity.

---

# 🎯 Objectives

- Calculate Electricity, Water, Gas, and Internet bills.
- Provide secure login for users and administrators.
- Store users' bill calculation history.
- Allow administrators to monitor user activities.
- Enable administrators to modify rate slabs and default charges.
- Reduce manual calculation errors.
- Provide a simple and user-friendly interface.

---

# ✨ Features

## User Features

- User Registration
- User Login
- Electricity Bill Calculation
- Water Bill Calculation
- Gas Bill Calculation
- Internet Bill Calculation
- View Bill History
- Logout

## Admin Features

- Admin Login
- View User Login Time
- View User Bill Calculation History
- Modify Default Bill Amount
- Update Rate Slabs
- Monitor User Activities

---

# 🧩 Modules

## 1. Login & Authentication Module

- User Login
- Admin Login
- Authentication Verification

---

## 2. Electricity Bill Module

- Calculate electricity bill based on units consumed.
- Display bill amount.

---

## 3. Water Bill Module

- Calculate water bill based on usage.

---

## 4. Gas Bill Module

- Calculate gas bill based on consumption.

---

## 5. Internet Bill Module

- Calculate internet bill using selected plan or default charges.

---

## 6. Bill History Module

- Store every calculated bill.
- Display previous bill records to the user.

---

## 7. Admin Management Module

- View user login records.
- View users' calculated bills.
- Update default bill amount.
- Modify billing rate slabs.

---

# 🛠️ Technologies Used

- Python
- JSON
- File Handling
- Object-Oriented Programming (OOP)

---

# 📂 Project Structure

```
Utility-Bill-Calculator-Suite/
│
├── main.py
├── login.py
├── admin.py
├── electricity.py
├── water.py
├── gas.py
├── internet.py
├── history.py
├── user_data.json
├── admin_data.json
├── bill_history.json
├── utils.py
└── README.md
```

---

# ▶️ How to Run

1. Install Python 3.x.

2. Clone the repository.

```bash
git clone https://github.com/your-username/Utility-Bill-Calculator-Suite.git
```

3. Navigate to the project folder.

```bash
cd Utility-Bill-Calculator-Suite
```

4. Run the application.

```bash
python main.py
```

---

# 📊 Expected Outcome

- Accurate calculation of Electricity, Water, Gas, and Internet bills.
- Secure authentication for users and administrators.
- Easy access to bill calculation history.
- Efficient monitoring of user activities by administrators.
- Flexible billing system through editable rate slabs and default charges.
- Reduced manual effort and improved billing accuracy.

---

# 🚀 Future Enhancements

- Graphical User Interface (Tkinter/PyQt)
- Database Integration (MySQL or SQLite)
- Online Bill Payment
- PDF Bill Generation
- Email Bill Notifications
- Monthly Usage Reports
- Mobile Application
- Cloud-Based Data Storage

---

# 👨‍💻 Author

**KISSHORE N**

Department of Computer Science and Engineering

---

# 📄 License

This project is developed for educational and academic purposes.
