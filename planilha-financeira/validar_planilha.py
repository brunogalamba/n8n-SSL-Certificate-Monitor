"""Valida as fórmulas da planilha contra um cálculo independente em Python.

Gera uma versão de teste (mesmas fórmulas, menos linhas), recalcula no
LibreOffice e compara os resultados em vários cenários:
  1. ano 2026 / setembro (mês corrente dos exemplos)
  2. ano 2027 / janeiro + filtro de categoria (virada de ano, parcelas que atravessam o ano)
Uso:  RECALC=/caminho/recalc.py python validar_planilha.py
"""
import calendar
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

os.environ["PFP_TESTE"] = "1"
import dados_exemplo as EX  # noqa: E402
import gerar_planilha as G  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

HOJE = dt.date.today()
TOL = 0.01
falhas, ok = [], 0


def check(nome, obtido, esperado):
    global ok
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        good = isinstance(obtido, (int, float)) and abs(obtido - esperado) <= TOL
    else:
        good = obtido == esperado
    if good:
        ok += 1
    else:
        falhas.append(f"{nome}: obtido={obtido!r} esperado={esperado!r}")


# ---------------------------------------------------- modelo independente
def venc_parcelas(data, fech, venc, n):
    """Data de fechamento da fatura da compra e 1º vencimento após ela (varredura dia a dia)."""
    if data.day < fech:
        fechamento = dt.date(data.year, data.month, fech)
    else:
        y, m = (data.year + 1, 1) if data.month == 12 else (data.year, data.month + 1)
        fechamento = dt.date(y, m, fech)
    v = fechamento + dt.timedelta(days=1)
    while v.day != min(venc, calendar.monthrange(v.year, v.month)[1]):
        v += dt.timedelta(days=1)
    out, y, m = [], v.year, v.month
    for _ in range(n):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


CARD = {c[0]: c for c in EX.CARTOES}
PARC = []  # (data compra, cat, cartão, (y,m), valor)
for d, desc, cat, cc, val, n in EX.COMPRAS:
    for ym in venc_parcelas(d, CARD[cc][3], CARD[cc][4], n):
        PARC.append((d, cat, cc, ym, val / n))


def mes(y, m):
    return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])


def modelo(y, m, cat=None):
    a, b = mes(y, m)
    r = {}
    r["rec"] = sum(v for d, _, _, v, _, _ in EX.RECEITAS if a <= d <= b)
    r["desp_conta"] = sum(x[3] for x in EX.DESPESAS if a <= x[0] <= b)
    r["cartao"] = sum(v for _, _, _, ym, v in PARC if ym == (y, m))
    r["desp"] = r["desp_conta"] + r["cartao"]
    ap = sum(v for d, _, op, v, _ in EX.MOVIMENTOS if a <= d <= b and op == "Aporte")
    rs = sum(v for d, _, op, v, _ in EX.MOVIMENTOS if a <= d <= b and op == "Resgate")
    r["aportes"] = ap - rs
    r["saldo"] = r["rec"] - r["desp"] - r["aportes"]
    cum_rec = sum(v for d, _, _, v, _, _ in EX.RECEITAS if d <= b)
    cum_desp = sum(x[3] for x in EX.DESPESAS if x[0] <= b)
    cum_card = sum(v for _, _, _, ym, v in PARC if ym <= (y, m))
    cum_ap = sum(v if op == "Aporte" else -v for d, _, op, v, _ in EX.MOVIMENTOS if d <= b and op in ("Aporte", "Resgate"))
    r["acum"] = EX.SALDO_INICIAL + cum_rec - cum_desp - cum_card - cum_ap
    r["invest"] = sum(-v if op == "Resgate" else v for d, _, op, v, _ in EX.MOVIMENTOS if d <= b)
    r["divida"] = sum(v for d, _, _, ym, v in PARC if d <= b and ym > (y, m))
    r["pl"] = r["acum"] + r["invest"] - r["divida"]
    if cat:
        r["cat"] = (sum(x[3] for x in EX.DESPESAS if a <= x[0] <= b and x[2] == cat)
                    + sum(v for _, c, _, ym, v in PARC if ym == (y, m) and c == cat))
    return r


def fatura(cc, y, m):
    return sum(v for _, _, c, ym, v in PARC if c == cc and ym == (y, m))


# ------------------------------------------------------------- execução
def recalc(src, dst):
    shutil.copy(src, dst)
    script = os.environ.get("RECALC")
    out = subprocess.run([sys.executable, script, dst, "600"], capture_output=True, text=True)
    res = json.loads(out.stdout)
    if res.get("status") != "success":
        print(json.dumps(res, indent=2, ensure_ascii=False))
        raise SystemExit("recálculo com erros")
    return load_workbook(dst, data_only=True)


def cenario(tmp, ano, mes_nome, cat="Todas"):
    base = os.path.join(tmp, "base.xlsx")
    G.build(base, exemplos=True)
    wb = load_workbook(base)
    ws = wb["Dashboard"]
    ws["C4"], ws["F4"], ws["J4"] = ano, mes_nome, cat
    p = os.path.join(tmp, f"cen_{ano}_{mes_nome}.xlsx")
    wb.save(p)
    return recalc(p, p.replace(".xlsx", "_calc.xlsx"))


def main():
    tmp = tempfile.mkdtemp()
    # ---------------- cenário 1: 2026 / setembro
    wb = cenario(tmp, 2026, "Setembro")
    res, dash = wb["Resumo Anual"], wb["Dashboard"]
    rows = {"rec": 30, "desp": 74, "cartao": 75, "desp_conta": 76, "aportes": 79, "saldo": 80,
            "acum": 81, "invest": 87, "divida": 88, "pl": 89}
    for m in range(1, 13):
        exp = modelo(2026, m)
        col = G.CL(1 + m)
        for k, r in rows.items():
            check(f"Resumo 2026 {m:02d} {k}", res[f"{col}{r}"].value, round(exp[k], 2))
        # soma das categorias == total (nada perdido/duplicado)
        soma = sum(res[f"{col}{rr}"].value or 0 for rr in range(33, 74))
        check(f"Resumo 2026 {m:02d} categorias=total", soma, round(exp["desp"], 2))
    check("KPI receitas set/26", dash["B7"].value, modelo(2026, 9)["rec"])
    check("KPI despesas set/26", dash["D7"].value, round(modelo(2026, 9)["desp"], 2))
    check("KPI saldo acumulado set/26", dash["H7"].value, round(modelo(2026, 9)["acum"], 2))
    check("KPI patrimônio set/26", dash["L7"].value, round(modelo(2026, 9)["pl"], 2))

    # cartões: matriz de faturas + casos de borda
    cc = wb["Cartões de Crédito"]
    for i, c in enumerate(EX.CARTOES):
        for m in range(1, 13):
            check(f"Fatura {c[0]} {m:02d}/2026", cc.cell(row=18 + i, column=1 + m).value, round(fatura(c[0], 2026, m), 2))
    r0 = G.R_CC[0]
    for i, (d, desc, cat, card, val, n) in enumerate(EX.COMPRAS):
        exp = venc_parcelas(d, CARD[card][3], CARD[card][4], n)[0]
        got = cc[f"H{r0 + i}"].value
        check(f"1º vencimento '{desc}' {d}", (got.year, got.month), exp)
    # limite utilizado = compras - pagamentos
    fat = wb["Faturas"]
    for i, c in enumerate(EX.CARTOES):
        compras = sum(x[4] for x in EX.COMPRAS if x[3] == c[0])
        pagos = sum(G.fatura_valor(ca, me) for ca, me in EX.FATURAS_MESES if ca == c[0] and (ca, me) not in EX.FATURAS_NAO_PAGAS)
        check(f"Limite utilizado {c[0]}", cc[f"G{6 + i}"].value, round(compras - pagos, 2))
    # status das faturas
    for i, (card, me) in enumerate(EX.FATURAS_MESES):
        r = G.R_FAT[0] + i
        venc = dt.date(me.year, me.month, CARD[card][4])
        if (card, me) not in EX.FATURAS_NAO_PAGAS:
            st = "Paga"
        elif venc < HOJE:
            st = "Vencida"
        elif (venc - HOJE).days <= EX.DIAS_ALERTA:
            st = f"Vence em {(venc - HOJE).days} dia(s)"
        else:
            st = "A vencer"
        check(f"Status fatura {card} {me:%m/%Y}", fat[f"H{r}"].value, st)
        check(f"Valor fatura {card} {me:%m/%Y}", fat[f"D{r}"].value, round(fatura(card, me.year, me.month), 2))

    # contas fixas no mês de setembro/2026
    cfs = wb["Contas Fixas"]
    for i, (conta, cat, val, dia, forma, ini, fim) in enumerate(EX.CONTAS_FIXAS):
        r = G.R_CF[0] + i
        pagos = [x for x in EX.DESPESAS if x[6] == conta and x[0].month == 9 and x[0].year == 2026]
        venc = dt.date(2026, 9, dia)
        if any(x[5] == "Pago" for x in pagos):
            st = "Paga"
        elif venc < HOJE:
            st = "Vencida"
        elif (venc - HOJE).days <= EX.DIAS_ALERTA:
            st = f"Vence em {(venc - HOJE).days} dia(s)"
        else:
            st = "Lançada (pendente)" if pagos else "A vencer"
        check(f"Status conta fixa {conta}", cfs[f"K{r}"].value, st)
    nao_lancado = sum(c[2] for c in EX.CONTAS_FIXAS if not any(x[6] == c[0] and x[0].month == 9 and x[0].year == 2026 for x in EX.DESPESAS))
    check("Contas fixas não lançadas set/26", cfs["F3"].value, nao_lancado)

    # pago x pendente (set/26)
    a, b = mes(2026, 9)
    pago = sum(x[3] for x in EX.DESPESAS if a <= x[0] <= b and x[5] == "Pago") + sum(
        G.fatura_valor(ca, me) for ca, me in EX.FATURAS_MESES if me == a and (ca, me) not in EX.FATURAS_NAO_PAGAS)
    pend = sum(x[3] for x in EX.DESPESAS if a <= x[0] <= b and x[5] == "Pendente") + max(
        0, modelo(2026, 9)["cartao"] - sum(G.fatura_valor(ca, me) for ca, me in EX.FATURAS_MESES if me == a and (ca, me) not in EX.FATURAS_NAO_PAGAS)) + nao_lancado
    check("KPI pago set/26", dash["B11"].value, round(pago, 2))
    check("KPI pendente set/26", dash["D11"].value, round(pend, 2))

    # orçamento set/26
    orc = wb["Orçamento Mensal"]
    for i, cat in enumerate(G.CAT_DESPESA):
        r = 7 + i
        real = modelo(2026, 9, cat)["cat"]
        prev = EX.ORCAMENTO.get(cat, 0)
        check(f"Orçamento realizado {cat}", orc[f"Q{r}"].value, round(real, 2))
        if prev and real > prev:
            check(f"Orçamento situação {cat}", orc[f"T{r}"].value, "Acima do orçamento")

    # metas
    mt = wb["Metas Financeiras"]
    reserva = sum(-v if op == "Resgate" else v for _, at, op, v, _ in EX.MOVIMENTOS if at == "Reserva de emergência (exemplo)")
    check("Meta vinculada ao investimento", mt["F7"].value, round(reserva, 2))
    check("Meta % realizado", mt["H7"].value, reserva / 30000)

    # comparativo entre anos (linha do ano selecionado)
    tot = [modelo(2026, m) for m in range(1, 13)]
    check("Comparativo 2026 receitas", res["B100"].value, sum(t["rec"] for t in tot))
    check("Comparativo 2026 despesas", res["C100"].value, round(sum(t["desp"] for t in tot), 2))
    check("Comparativo 2026 patrimônio", res["F100"].value, round(tot[-1]["pl"], 2))

    # ---------------- cenário 2: 2027 / janeiro com filtro de categoria
    cat = "Eletrônicos e eletrodomésticos"
    wb = cenario(tmp, 2027, "Janeiro", cat)
    res, dash = wb["Resumo Anual"], wb["Dashboard"]
    for m in range(1, 13):
        exp = modelo(2027, m, cat)
        col = G.CL(1 + m)
        for k, r in rows.items():
            check(f"Resumo 2027 {m:02d} {k}", res[f"{col}{r}"].value, round(exp[k], 2))
        check(f"Dashboard categoria 2027 {m:02d}", dash[f"P{75 + m}"].value, round(exp["cat"], 2))
    check("KPI categoria jan/27", dash["H15"].value, round(modelo(2027, 1, cat)["cat"], 2))
    check("Variação patrimonial jan/27 (virada de ano)", res["B90"].value,
          round(modelo(2027, 1)["pl"] - modelo(2026, 12)["pl"], 2))
    check("Comparativo 2026 visto de 2027", res["B99"].value, sum(modelo(2026, m)["rec"] for m in range(1, 13)))

    print(f"Verificações OK: {ok}  |  Falhas: {len(falhas)}")
    for f in falhas:
        print("  FALHA:", f)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
