CREATE DATABASE IF NOT EXISTS products_db;
USE products_db;

-- Создаём пользователя с нужным типом авторизации
CREATE USER IF NOT EXISTS 'nurtas'@'%' IDENTIFIED WITH mysql_native_password BY 'nurtas05';

GRANT ALL PRIVILEGES ON products_db.* TO 'nurtas'@'%';
FLUSH PRIVILEGES;

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0 CHECK (stock >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_name ON products(name);

INSERT INTO products (name, description, price, stock)
VALUES
('Laptop', 'Lightweight laptop for work and study', 999.99, 10),
('Headphones', 'Noise-cancelling over-ear headphones', 199.99, 25),
('Smartphone', 'High-end Android phone with 128GB storage', 699.00, 15);
