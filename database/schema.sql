CREATE DATABASE IF NOT EXISTS customer_analytics;
USE customer_analytics;
CREATE TABLE IF NOT EXISTS transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_no VARCHAR(30) NOT NULL, customer_id VARCHAR(30) NOT NULL,
  invoice_date DATETIME NOT NULL, stock_code VARCHAR(30), description VARCHAR(255),
  quantity INT NOT NULL, unit_price DECIMAL(12,2) NOT NULL, revenue DECIMAL(14,2) NOT NULL,
  country VARCHAR(80),
  INDEX idx_customer (customer_id), INDEX idx_invoice (invoice_no), INDEX idx_date (invoice_date)
);
CREATE TABLE IF NOT EXISTS customers (
  customer_id VARCHAR(30) PRIMARY KEY,
  first_purchase_date DATETIME, last_purchase_date DATETIME,
  total_orders INT, total_revenue DECIMAL(14,2), recency INT, frequency INT,
  monetary_value DECIMAL(14,2), avg_order_value DECIMAL(14,2), lifetime_days INT,
  r_score TINYINT, f_score TINYINT, m_score TINYINT,
  segment VARCHAR(40), predicted_clv DECIMAL(14,2),
  INDEX idx_segment (segment)
);
