# 🎯 Endpoints de Metas do Usuário

## 📋 Visão Geral

Implementei dois novos endpoints para gerenciar metas dos usuários:

1. **`POST /metrics/goals`** - Buscar metas do usuário
2. **`POST /metrics/goals/update`** - Atualizar metas (apenas admin)

## 🔍 **POST /metrics/goals**

### Descrição
Busca as metas configuradas para uma tabela específica.

### Autenticação
```http
Authorization: Bearer <seu_token_jwt>
```

### Body
```json
{
  "table_name": "constance"
}
```

### Resposta
```json
{
  "username": "constance",
  "goals": {
    "revenue_goal": 100000.0,
    "orders_goal": 1000,
    "conversion_rate_goal": 5.0,
    "roas_goal": 8.0,
    "new_customers_goal": 100
  },
  "message": "Metas carregadas com sucesso"
}
```

### Metas Padrão
Se nenhuma meta for encontrada, o sistema retorna metas padrão:
- **revenue_goal**: R$ 100.000,00
- **orders_goal**: 1.000 pedidos
- **conversion_rate_goal**: 5,0%
- **roas_goal**: 8,0
- **new_customers_goal**: 100 novos clientes

### Lógica de Busca
1. **Usuário com acesso total** (`tablename = 'all'`): Pode buscar metas de qualquer tabela
2. **Usuário com acesso limitado**: Só pode buscar metas da sua própria tabela

---

## ✏️ **POST /metrics/goals/update**

### Descrição
Atualiza as metas de um usuário específico (apenas administradores).

### Autenticação
```http
Authorization: Bearer <seu_token_jwt>
```

### Body
```json
{
  "username": "constance",
  "goals": {
    "revenue_goal": 150000.0,
    "orders_goal": 1500,
    "conversion_rate_goal": 6.5,
    "roas_goal": 10.0,
    "new_customers_goal": 200,
    "custom_goal": "Meta personalizada"
  }
}
```

### Resposta
```json
{
  "message": "Metas atualizadas com sucesso",
  "username": "constance",
  "goals": {
    "revenue_goal": 150000.0,
    "orders_goal": 1500,
    "conversion_rate_goal": 6.5,
    "roas_goal": 10.0,
    "new_customers_goal": 200,
    "custom_goal": "Meta personalizada"
  },
  "updated_at": "2024-01-15T10:30:00"
}
```

### Permissões
- **Apenas administradores** podem atualizar metas
- Retorna erro 403 se o usuário não for admin

---

## 🗄️ **Estrutura da Tabela**

### Tabela: `mymetric-hub-shopify.dbt_config.user_goals`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `username` | STRING | Nome da tabela/usuário |
| `goals` | JSON | Metas em formato JSON |

### Exemplo de Dados
```sql
INSERT INTO `mymetric-hub-shopify.dbt_config.user_goals` 
(username, goals) VALUES 
('constance', '{"revenue_goal": 100000.0, "orders_goal": 1000}'),
('havaianas', '{"revenue_goal": 200000.0, "orders_goal": 2000}');
```

---

## 🔧 **Implementação Técnica**

### Query de Busca
```sql
SELECT goals
FROM `mymetric-hub-shopify.dbt_config.user_goals`
WHERE username = '{tablename}'
LIMIT 1
```

### Query de Atualização (MERGE)
```sql
MERGE `mymetric-hub-shopify.dbt_config.user_goals` AS target
USING (SELECT '{username}' as username) AS source
ON target.username = source.username
WHEN MATCHED THEN
    UPDATE SET goals = '{goals}'
WHEN NOT MATCHED THEN
    INSERT (username, goals) VALUES ('{username}', '{goals}')
```

---

## 📊 **Casos de Uso**

### 1. **Dashboard com Metas**
```javascript
// Buscar metas do usuário
const goals = await fetch('/metrics/goals', {
    method: 'POST',
    headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        table_name: 'constance'
    })
});

// Comparar performance atual com metas
const performance = await fetch('/metrics/basic-data', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify(requestData)
});

// Calcular progresso
const progress = (performance.summary.total_receita / goals.goals.revenue_goal) * 100;
```

### 2. **Configuração de Metas (Admin)**
```javascript
// Atualizar metas de um cliente
const updateGoals = await fetch('/metrics/goals/update', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${adminToken}` },
  body: JSON.stringify({
    username: 'constance',
    goals: {
      revenue_goal: 150000.0,
      orders_goal: 1500,
      conversion_rate_goal: 6.5
    }
  })
});
```

---

## 🚨 **Tratamento de Erros**

### Erros Comuns

| Código | Descrição | Solução |
|--------|-----------|---------|
| 401 | Não autorizado | Verificar token JWT |
| 403 | Acesso negado | Apenas admins podem atualizar metas |
| 404 | Usuário não encontrado | Verificar se o usuário existe |
| 500 | Erro interno | Verificar logs do servidor |

### Logs de Debug
```
🔓 Usuário com acesso total usando tabela padrão para metas: constance
🔒 Usuário com acesso limitado usando tabela para metas: havaianas
Executando query de metas: SELECT goals FROM `mymetric-hub-shopify.dbt_config.user_goals` WHERE username = 'constance' LIMIT 1
```

---

## 📈 **Benefícios**

1. **Metas Personalizadas**: Cada cliente pode ter suas próprias metas
2. **Flexibilidade**: Suporte a metas customizadas além das padrão
3. **Segurança**: Apenas administradores podem modificar metas
4. **Fallback**: Metas padrão quando nenhuma configuração existe
5. **Integração**: Fácil integração com dashboards existentes

---

## 🔄 **Próximos Passos**

1. **Integrar com Dashboard**: Usar metas para mostrar progresso
2. **Alertas**: Notificações quando metas não são atingidas
3. **Histórico**: Rastrear mudanças nas metas ao longo do tempo
4. **Relatórios**: Relatórios de performance vs metas 