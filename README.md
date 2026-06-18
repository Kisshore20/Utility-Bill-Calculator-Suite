# ⚡ Utility Bill Calculator Suite

A web-based **Utility Bill Calculator Suite** developed using **Python (Flask), HTML, CSS, JavaScript, and SQLite**. The application allows users to calculate **Electricity, Water, Gas, and Internet bills**, maintain bill history, and provides an **Admin Dashboard** for monitoring user activities and managing billing rates.

---

## 📌 Project Overview

The Utility Bill Calculator Suite is designed to simplify utility bill management by providing a centralized platform for calculating multiple utility bills. The application offers separate interfaces for users and administrators.

Users can securely log in, calculate utility bills, and view their previous bill history. Administrators can monitor user login activities, view calculated bills, and update default bill amounts and rate slabs without modifying the source code.

---

## 🎯 Problem Statement

Manual utility bill calculation is often time-consuming and prone to human errors. Users also lack a convenient way to store previous bill records, while administrators need an easy method to manage changing utility rates.

This project provides an automated solution for calculating utility bills, maintaining bill history, and allowing administrators to efficiently manage billing parameters through a secure web interface.

---

# 🎯 Objectives

- Develop an automated utility bill calculation system.
- Calculate Electricity, Water, Gas, and Internet bills.
- Maintain user bill history.
- Provide secure login for Users and Admin.
- Allow administrators to monitor user activities.
- Enable administrators to modify default bill amounts.
- Allow administrators to update utility rate slabs.
- Reduce manual calculation errors.

---

# ✨ Features

## 👤 User Features

- User Login
- Calculate Electricity Bill
- Calculate Water Bill
- Calculate Gas Bill
- Calculate Internet Bill
- View Bill History
- Logout

---

## 👨‍💼 Admin Features

- Secure Admin Login
- View User Login History
- View User Bill Calculation History
- Modify Default Bill Amount
- Update Utility Rate Slabs
- Logout

---

# 🧩 Modules

### 1. Authentication Module
- User Login
- Admin Login
- Session Management

### 2. Electricity Bill Module
- Calculates electricity bill based on unit consumption.

### 3. Water Bill Module
- Calculates water bill using water consumption.

### 4. Gas Bill Module
- Calculates gas bill according to gas usage.

### 5. Internet Bill Module
- Calculates internet bill based on selected plan or usage.

### 6. Bill History Module
- Stores calculated bills.
- Displays previous bill records.

### 7. Admin Management Module
- View user login records.
- View user bill history.
- Update default charges.
- Modify utility rate slabs.

---

# 🛠️ Technologies Used

| Technology | Purpose |
|------------|----------|
| Python | Backend Logic |
| Flask | Web Framework |
| HTML5 | Frontend |
| CSS3 | Styling |
| JavaScript | Client-side Functionality |
| SQLite | Database |
| Git | Version Control |
| GitHub | Project Hosting |

---

# 📂 Project Structure

```
Utility-Bill-Calculator-Suite/
│
├── app.py
├── requirements.txt
├── history.db
├── login.html
├── home.html
├── admin.html
├── index.html
├── Project Details.md
├── Proposed_Architecture.png
├── Use Case Diagram.png
├── README.md
└── __pycache__/
```

---

# 🗄️ Database

The application uses **SQLite** to store:

- User Details
- Login History
- Bill History
- Default Bill Amount
- Rate Slabs

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/Kisshore20/Utility-Bill-Calculator-Suite.git
```

---

## Navigate to Project Folder

```bash
cd Utility-Bill-Calculator-Suite
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Application

```bash
python app.py
```

---

## Open in Browser

```
http://127.0.0.1:5000
```

---

# 📊 Expected Output

- Secure login system
- Accurate utility bill calculations
- Bill history tracking
- Admin dashboard for monitoring users
- Dynamic modification of billing rates
- User-friendly interface
- Fast and reliable bill management

---

# 🖼️ Project Architecture

See:

- **Proposed_Architecture.png**

---

# 📋 Use Case Diagram

See:

- **Use Case Diagram.png**

---

# 🔮 Future Enhancements

- Online Bill Payment
- PDF Bill Generation
- Email Notifications
- Monthly Usage Reports
- Charts and Analytics Dashboard
- Mobile Application
- Cloud Database Integration
- Multi-language Support

---

# 📜 License

This project is developed for educational and academic purposes.

---

# 👨‍💻 Author

**Kisshore**

Department of Computer Science and Engineering

---

⭐ If you found this project useful, don't forget to star the repository!
