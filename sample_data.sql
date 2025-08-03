-- Exemplos de queries SQL para criar dados de teste no BigQuery
-- Execute estas queries no BigQuery Console para testar a API

-- 1. Criar tabela de usuários (se não existir)
CREATE TABLE IF NOT EXISTS `mymetric-hub-shopify.dbt_config.users` (
  email STRING,
  admin BOOLEAN,
  access_control STRING,
  tablename STRING,
  password STRING
);

-- 2. Inserir usuários de exemplo
-- Senhas hashadas com SHA-256 (senha123 = a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3)
INSERT INTO `mymetric-hub-shopify.dbt_config.users` 
(email, admin, access_control, tablename, password)
VALUES 
('admin@exemplo.com', true, 'full', 'admin_metrics', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'),
('usuario@exemplo.com', false, 'read', 'user_metrics', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3');

-- 3. Criar tabela de métricas de exemplo para admin
CREATE TABLE IF NOT EXISTS `mymetric-hub-shopify.admin_metrics` (
  date DATE,
  order_id STRING,
  customer_id STRING,
  customer_name STRING,
  product_name STRING,
  quantity INT64,
  revenue FLOAT64,
  session_id STRING
);

-- 4. Inserir dados de exemplo para admin
INSERT INTO `mymetric-hub-shopify.admin_metrics` (date, order_id, customer_id, customer_name, product_name, quantity, revenue, session_id)
VALUES 
('2024-01-15', 'ORD001', 'CUST001', 'João Silva', 'Produto A', 2, 150.00, 'SESS001'),
('2024-01-15', 'ORD002', 'CUST002', 'Maria Santos', 'Produto B', 1, 200.00, 'SESS002'),
('2024-01-14', 'ORD003', 'CUST003', 'Pedro Costa', 'Produto C', 3, 75.00, 'SESS003'),
('2024-01-14', 'ORD004', 'CUST004', 'Ana Oliveira', 'Produto A', 1, 75.00, 'SESS004'),
('2024-01-13', 'ORD005', 'CUST005', 'Carlos Lima', 'Produto B', 2, 400.00, 'SESS005'),
('2024-01-13', 'ORD006', 'CUST006', 'Lucia Ferreira', 'Produto C', 1, 25.00, 'SESS006'),
('2024-01-12', 'ORD007', 'CUST007', 'Roberto Alves', 'Produto A', 4, 300.00, 'SESS007'),
('2024-01-12', 'ORD008', 'CUST008', 'Fernanda Costa', 'Produto B', 1, 200.00, 'SESS008'),
('2024-01-11', 'ORD009', 'CUST009', 'Marcos Silva', 'Produto C', 2, 50.00, 'SESS009'),
('2024-01-11', 'ORD010', 'CUST010', 'Patricia Lima', 'Produto A', 1, 75.00, 'SESS010');

-- 5. Criar tabela de métricas de exemplo para usuário
CREATE TABLE IF NOT EXISTS `mymetric-hub-shopify.user_metrics` (
  date DATE,
  order_id STRING,
  customer_id STRING,
  customer_name STRING,
  product_name STRING,
  quantity INT64,
  revenue FLOAT64,
  session_id STRING
);

-- 6. Inserir dados de exemplo para usuário
INSERT INTO `mymetric-hub-shopify.user_metrics` (date, order_id, customer_id, customer_name, product_name, quantity, revenue, session_id)
VALUES 
('2024-01-15', 'UORD001', 'UCUST001', 'João Usuario', 'Produto X', 1, 100.00, 'USESS001'),
('2024-01-14', 'UORD002', 'UCUST002', 'Maria Usuario', 'Produto Y', 2, 180.00, 'USESS002'),
('2024-01-13', 'UORD003', 'UCUST003', 'Pedro Usuario', 'Produto Z', 1, 120.00, 'USESS003');

-- 7. Query para verificar os dados inseridos
SELECT 'Usuários' as tabela, COUNT(*) as total FROM `mymetric-hub-shopify.dbt_config.users`
UNION ALL
SELECT 'Admin Metrics' as tabela, COUNT(*) as total FROM `mymetric-hub-shopify.admin_metrics`
UNION ALL
SELECT 'User Metrics' as tabela, COUNT(*) as total FROM `mymetric-hub-shopify.user_metrics`;

-- 8. Query para testar métricas de receita
SELECT 
  DATE(date) as date,
  SUM(revenue) as daily_revenue
FROM `mymetric-hub-shopify.admin_metrics`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY DATE(date)
ORDER BY date;

-- 9. Query para testar produtos mais vendidos
SELECT 
  product_name,
  SUM(quantity) as total_quantity,
  SUM(revenue) as total_revenue
FROM `mymetric-hub-shopify.admin_metrics`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY product_name
ORDER BY total_revenue DESC
LIMIT 5; 