-- Run this in your MySQL to add the Student Feedback table
USE library_db;

CREATE TABLE IF NOT EXISTS student_feedback (
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

SELECT 'student_feedback table created successfully!' AS status;
