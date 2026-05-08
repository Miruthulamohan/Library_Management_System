-- ============================================================
--  Library Management System - Complete Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_db;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS membership_cards;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS issued_books;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS library_visitors;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- Users
CREATE TABLE users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    role        ENUM('admin','student') NOT NULL DEFAULT 'student',
    phone       VARCHAR(20),
    address     TEXT,
    member_id   VARCHAR(20) UNIQUE,
    is_active   TINYINT(1) DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Books
CREATE TABLE books (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    author         VARCHAR(150) NOT NULL,
    isbn           VARCHAR(50) UNIQUE,
    category       VARCHAR(100),
    total_copies   INT DEFAULT 1,
    available      INT DEFAULT 1,
    cover_url      VARCHAR(255),
    description    TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Issued Books
CREATE TABLE issued_books (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    book_id      INT NOT NULL,
    user_id      INT NOT NULL,
    issued_date  DATE NOT NULL,
    due_date     DATE NOT NULL,
    return_date  DATE,
    fine         DECIMAL(8,2) DEFAULT 0.00,
    fine_paid    TINYINT(1) DEFAULT 0,
    status       ENUM('issued','returned','overdue') DEFAULT 'issued',
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Membership Cards
CREATE TABLE membership_cards (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL UNIQUE,
    plan         ENUM('basic','standard','premium') DEFAULT 'basic',
    amount       DECIMAL(8,2) DEFAULT 0.00,
    txn_id       VARCHAR(100),
    payment_date TIMESTAMP,
    status       ENUM('pending','approved','rejected') DEFAULT 'pending',
    approved_at  TIMESTAMP,
    start_date   DATE,
    end_date     DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Payments (fines)
CREATE TABLE payments (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    issued_id  INT,
    amount     DECIMAL(8,2) NOT NULL,
    method     VARCHAR(50) DEFAULT 'qr',
    txn_id     VARCHAR(100),
    paid_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (issued_id) REFERENCES issued_books(id)
);

-- Events
CREATE TABLE events (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    event_date  DATE,
    event_time  TIME,
    venue       VARCHAR(200),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE notifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT,
    title      VARCHAR(200) NOT NULL,
    message    TEXT,
    type       VARCHAR(50) DEFAULT 'info',
    is_read    TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Library Visitors (who is in library)
CREATE TABLE library_visitors (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    check_in   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_out  TIMESTAMP NULL DEFAULT NULL,
    status     ENUM('in','out') DEFAULT 'in',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Student Feedback
CREATE TABLE student_feedback (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    category     ENUM('general','books','staff','facilities','suggestions') DEFAULT 'general',
    subject      VARCHAR(200) NOT NULL,
    message      TEXT NOT NULL,
    rating       TINYINT CHECK (rating BETWEEN 1 AND 5),
    is_read      TINYINT(1) DEFAULT 0,
    admin_reply  TEXT,
    replied_at   TIMESTAMP NULL DEFAULT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Default admin (password: Library@2024)
INSERT INTO users (name, email, password, role, member_id)
VALUES ('Library Admin', 'admin@library.com',
'$2b$12$pHBmmZpHnCIKnC.dVktGCuRITxenIufoTQ8dWWTLo23rIvXzBJqfm', 'admin', 'ADMIN001');