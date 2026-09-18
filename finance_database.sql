USE finance_db;
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    date DATE,
    description VARCHAR(255),
    amount DECIMAL(10,2),
    type VARCHAR(20),
    category VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE budgets (
    budget_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    month VARCHAR(20),
    category VARCHAR(50),
    limit_amount DECIMAL(10,2),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT,
    predicted_category VARCHAR(50),
    confidence DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE insights (
    insight_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    insight_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

SHOW TABLES;

USE finance_db;

SELECT user_id, name, email, password_hash
FROM users;

USE finance_db;

SELECT *
FROM transactions;

USE finance_db;

SELECT * FROM budgets;


USE finance_db;

SELECT * FROM predictions;

USE finance_db;

SELECT * FROM users;

SELECT * FROM transactions;

SELECT * FROM predictions;

SELECT * FROM budgets;

USE finance_db;
SELECT * FROM users;
SELECT * FROM transactions;
SELECT * FROM budgets;
SELECT * FROM predictions;
SELECT * FROM insights;


