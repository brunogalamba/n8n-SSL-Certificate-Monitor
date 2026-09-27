"""Dados FICTÍCIOS usados apenas para demonstrar o funcionamento da planilha.

Nenhum valor aqui representa informação financeira real. Todos os itens
levam o sufixo "(exemplo)" e podem ser apagados na planilha.
"""
import datetime as dt

D = dt.date
HOJE_REF = D(2026, 9, 27)  # data usada para definir status "Pago"/"Recebido" dos exemplos

SALDO_INICIAL = 3000.00
DIAS_ALERTA = 5

# --------------------------------------------------------------------- Receitas
# (data, descrição, categoria, valor, status, observação)
RECEITAS = []
for m in range(1, 13):
    d = D(2026, m, 5)
    RECEITAS.append((d, "Salário (exemplo)", "Salário", 5000.00,
                     "Recebido" if d <= HOJE_REF else "A receber", ""))
RECEITAS += [
    (D(2026, 3, 15), "Freelance (exemplo)", "Renda extra / freelance", 800.00, "Recebido", ""),
    (D(2026, 7, 18), "Freelance (exemplo)", "Renda extra / freelance", 1200.00, "Recebido", ""),
    (D(2026, 11, 30), "13º salário - 1ª parcela (exemplo)", "13º salário", 2500.00, "A receber", ""),
    (D(2026, 12, 18), "13º salário - 2ª parcela (exemplo)", "13º salário", 2500.00, "A receber", ""),
    (D(2027, 1, 5), "Salário (exemplo)", "Salário", 5200.00, "A receber", "Teste de virada de ano"),
]
RECEITAS.sort(key=lambda r: r[0])

# ----------------------------------------------------------------- Contas fixas
# (conta, categoria, valor previsto, dia venc., forma, início, fim)
CONTAS_FIXAS = [
    ("Aluguel (exemplo)", "Moradia", 1500.00, 10, "Boleto", D(2026, 1, 1), None),
    ("Energia elétrica (exemplo)", "Contas de consumo (água, luz, gás)", 180.00, 15, "Débito automático", D(2026, 1, 1), None),
    ("Internet (exemplo)", "Telefone e internet", 120.00, 20, "Débito automático", D(2026, 1, 1), None),
    ("Plano de saúde (exemplo)", "Saúde", 450.00, 8, "Boleto", D(2026, 1, 1), None),
    ("Academia (exemplo)", "Cuidados pessoais", 100.00, 5, "Pix", D(2026, 1, 1), D(2026, 12, 31)),
]

# --------------------------------------------------------------------- Despesas
# (data, descrição, categoria, valor, forma, status, conta fixa vinculada, obs)
DESPESAS = []
for m in range(1, 10):
    energia = 160.00 + 5 * m
    DESPESAS += [
        (D(2026, m, 5), "Academia (exemplo)", "Cuidados pessoais", 100.00, "Pix", "Pago", "Academia (exemplo)", ""),
        (D(2026, m, 8), "Plano de saúde (exemplo)", "Saúde", 450.00, "Boleto", "Pago", "Plano de saúde (exemplo)", ""),
        (D(2026, m, 10), "Aluguel (exemplo)", "Moradia", 1500.00, "Boleto", "Pago", "Aluguel (exemplo)", ""),
        (D(2026, m, 3), "Supermercado (exemplo)", "Supermercado", 520.00 + 10 * m, "Pix", "Pago", "", ""),
        (D(2026, m, 18), "Supermercado (exemplo)", "Supermercado", 430.00, "Cartão de débito", "Pago", "", ""),
        (D(2026, m, 12), "Combustível (exemplo)", "Transporte", 250.00, "Cartão de débito", "Pago", "", ""),
    ]
    if m < 9:
        DESPESAS += [
            (D(2026, m, 15), "Energia elétrica (exemplo)", "Contas de consumo (água, luz, gás)", energia, "Débito automático", "Pago", "Energia elétrica (exemplo)", ""),
            (D(2026, m, 20), "Internet (exemplo)", "Telefone e internet", 120.00, "Débito automático", "Pago", "Internet (exemplo)", ""),
        ]
    else:  # setembro: energia lançada mas pendente; internet não lançada
        DESPESAS.append((D(2026, 9, 15), "Energia elétrica (exemplo)", "Contas de consumo (água, luz, gás)", energia, "Boleto", "Pendente", "Energia elétrica (exemplo)", "Teste: conta vencida"))
DESPESAS += [
    (D(2026, 1, 20), "IPVA (exemplo)", "Impostos e taxas", 1200.00, "Boleto", "Pago", "", ""),
    (D(2026, 4, 22), "Farmácia (exemplo)", "Saúde", 85.00, "Pix", "Pago", "", ""),
    (D(2026, 10, 2), "Consulta médica (exemplo)", "Saúde", 300.00, "Pix", "Pendente", "", "Teste: vence em poucos dias"),
]
DESPESAS.sort(key=lambda r: r[0])

# --------------------------------------------------------------------- Cartões
# (nome, bandeira, limite, dia fechamento, dia vencimento)
CARTOES = [
    ("Cartão A (exemplo)", "Visa", 8000.00, 25, 5),       # vencimento no mês seguinte ao fechamento
    ("Cartão B (exemplo)", "Mastercard", 5000.00, 3, 10),  # vencimento no mesmo mês do fechamento
]

# (data, descrição, categoria, cartão, valor total, nº parcelas)
COMPRAS = []
for m in range(1, 10):
    COMPRAS.append((D(2026, m, 10), "Restaurante (exemplo)", "Alimentação", "Cartão A (exemplo)", 180.00, 1))
    COMPRAS.append((D(2026, m, 15), "Streaming (exemplo)", "Assinaturas e serviços", "Cartão B (exemplo)", 40.00, 1))
COMPRAS += [
    (D(2026, 1, 24), "Tênis (exemplo) - 1 dia antes do fechamento", "Vestuário", "Cartão A (exemplo)", 300.00, 3),
    (D(2026, 1, 25), "Livros (exemplo) - no dia do fechamento", "Educação", "Cartão A (exemplo)", 150.00, 1),
    (D(2026, 3, 15), "Notebook (exemplo)", "Eletrônicos e eletrodomésticos", "Cartão A (exemplo)", 4800.00, 12),
    (D(2026, 5, 2), "Presente (exemplo)", "Presentes e doações", "Cartão B (exemplo)", 200.00, 1),
    (D(2026, 5, 3), "Farmácia (exemplo) - no dia do fechamento", "Saúde", "Cartão B (exemplo)", 90.00, 1),
    (D(2026, 7, 25), "Passagem aérea (exemplo)", "Viagens", "Cartão A (exemplo)", 1800.00, 6),
    (D(2026, 11, 20), "Geladeira (exemplo) - atravessa o ano", "Eletrônicos e eletrodomésticos", "Cartão B (exemplo)", 3000.00, 10),
]
COMPRAS.sort(key=lambda r: r[0])

# Faturas: pagas integralmente até ago/2026; set/2026 paga no Cartão A e em aberto no B;
# out/2026 do Cartão A registrada ainda sem pagamento. Valores pagos calculados em gerar_planilha.
FATURAS_MESES = [(c[0], D(2026, m, 1)) for c in CARTOES for m in range(1, 11)]
FATURAS_NAO_PAGAS = {("Cartão B (exemplo)", D(2026, 9, 1)), ("Cartão A (exemplo)", D(2026, 10, 1)),
                     ("Cartão B (exemplo)", D(2026, 10, 1))}

# --------------------------------------------------------------- Investimentos
# (ativo, tipo, instituição)
ATIVOS = [
    ("Reserva de emergência (exemplo)", "Reserva de emergência", "Banco (exemplo)"),
    ("Tesouro IPCA+ (exemplo)", "Tesouro Direto", "Corretora (exemplo)"),
    ("Fundo imobiliário (exemplo)", "Fundos imobiliários (FII)", "Corretora (exemplo)"),
]
# (data, ativo, operação, valor, obs)
MOVIMENTOS = []
_saldo_reserva = 0.0
for m in range(1, 10):
    MOVIMENTOS.append((D(2026, m, 6), "Reserva de emergência (exemplo)", "Aporte", 500.00, ""))
    _saldo_reserva += 500
    if m == 7:
        MOVIMENTOS.append((D(2026, 7, 20), "Reserva de emergência (exemplo)", "Resgate", 300.00, "Teste de resgate"))
        _saldo_reserva -= 300
    rend = round(_saldo_reserva * 0.008, 2)
    MOVIMENTOS.append((D(2026, m, 28 if m != 2 else 27), "Reserva de emergência (exemplo)", "Rendimento", rend, ""))
    _saldo_reserva += rend
MOVIMENTOS += [
    (D(2026, 3, 10), "Tesouro IPCA+ (exemplo)", "Aporte", 1000.00, ""),
    (D(2026, 6, 10), "Tesouro IPCA+ (exemplo)", "Aporte", 1000.00, ""),
    (D(2026, 6, 30), "Tesouro IPCA+ (exemplo)", "Rendimento", 45.00, ""),
    (D(2026, 9, 25), "Tesouro IPCA+ (exemplo)", "Rendimento", 38.50, ""),
    (D(2026, 4, 10), "Fundo imobiliário (exemplo)", "Aporte", 800.00, ""),
    (D(2026, 8, 15), "Fundo imobiliário (exemplo)", "Rendimento", -25.00, "Desvalorização (valor negativo)"),
]
MOVIMENTOS.sort(key=lambda r: r[0])

# ----------------------------------------------------------------------- Metas
# (meta, valor alvo, prazo, ativo vinculado, valor acumulado manual)
METAS = [
    ("Reserva de emergência (exemplo)", 30000.00, D(2027, 12, 31), "Reserva de emergência (exemplo)", None),
    ("Viagem de férias (exemplo)", 8000.00, D(2027, 6, 30), "", 1500.00),
    ("Troca de carro (exemplo)", 40000.00, D(2028, 12, 31), "", 5000.00),
]

# ------------------------------------------------------------------- Orçamento
# categoria -> valor mensal previsto (igual para os 12 meses no exemplo)
ORCAMENTO = {
    "Moradia": 1500, "Supermercado": 1000, "Alimentação": 200, "Transporte": 300,
    "Saúde": 500, "Contas de consumo (água, luz, gás)": 200, "Telefone e internet": 120,
    "Assinaturas e serviços": 50, "Cuidados pessoais": 100, "Vestuário": 100,
    "Eletrônicos e eletrodomésticos": 400, "Viagens": 300, "Impostos e taxas": 100,
}
