# 🤖 מודל האלגוריתם המלא - Sniper Bot V2.0

---

## ארכיטקטורה

```
שלב 1: DATA INGESTION (איסוף נתונים)
    ↓
שלב 2: PRESSURE COOKER FILTER (6 קריטריונים)
    ↓
שלב 3: LENS SCORING (4 עדשות)
    ↓
שלב 4: TOP 3 SELECTION (בחירת טופ 3)
    ↓
שלב 5: PAPER TRADING (SL/TP)
    ↓
שלב 6: SELF-LEARNING (Gradient Descent)
```

---

## שלב 1: איסוף נתונים

**מקורות:** NASDAQ Trader, Yahoo Finance, FMP API

**סינון ראשוני:**
- הסר ETFs, ADRs, Warrants
- מחיר: $5-$1000
- נפח יומי: >100,000

**תוצאה:** ~8,000 → ~2,000 מניות

---

## שלב 2: פילטר "סיר הלחץ"

### נוסחאות:

**RSI:**
```
RSI = 100 - (100 / (1 + RS))
RS = ממוצע רווחים / ממוצע הפסדים (14 יום)
כלל: 50 ≤ RSI ≤ 75
```

**RVOL:**
```
RVOL = נפח נוכחי / ממוצע נפח (10 ימים)
כלל: RVOL ≥ 1.5
```

**שינוי יומי:**
```
Daily_Change = (סגירה - סגירה אתמול) / סגירה אתמול × 100
כלל: 2% ≤ Daily_Change ≤ 10%
```

**Bollinger Width:**
```
BB_Width = (סטיית תקן × 4) / SMA(20)
כלל: BB_Width < 0.15
```

**מרחק משיא:**
```
Pct_From_High = מחיר / שיא 52 שבועות × 100
כלל: Pct_From_High ≥ 95%
```

**יישור EMA:**
```
כלל: מחיר > EMA(20) > EMA(50)
```

**תוצאה:** ~2,000 → ~10-15 מניות

---

## שלב 3: ציון עדשות

| עדשה | תפקיד | משקל |
|------|-------|------|
| QUANT | בעלות מוסדית | 1.0 |
| ORACLE | דירוג אנליסטים | 0.8 |
| **HUNTER** | **קניות אינסיידרים** | **1.5** |
| CHARTIST | RSI, מגמה | 1.2 |

---

## שלב 4: בחירת Top 3

**נוסחה:**
```
Score = RVOL_Score (max 30) + BlueSky_Score (max 30) + 
        RSI_Score (max 20) + Momentum_Score (max 20)
```

---

## שלב 5: מסחר נייר

### פרמטרים:
- הון: $100,000
- פוזיציה: $2,000
- מקסימום: 3/יום

### כללי יציאה:

| כלל | תנאי | פעולה |
|-----|------|-------|
| Stop Loss | ≤-3% | SELL 100% |
| Take Profit 1 | ≥+5% | SELL 50%, SL→breakeven |
| Take Profit 2 | ≥+10% | SELL remaining |
| Time Stop | 48h, <1% move | SELL 100% |

---

## שלב 6: למידה עצמית

### תקופות בדיקה:
10, 20, 30, 40, 50, 60 יום

### סיווג:
- WIN: ≥+10%
- LOSS: ≤-5%
- HOLD: בין לבין

### Gradient Descent פרופורציונלי:
```
Proportion[lens] = Score[lens] / Total_Score
Adjustment = Direction × 0.02 × Proportion × Period_Weight
New_Weight = clamp(Old + Adjustment, 0.3, 2.0)
```

---

## טבלת כללים מסכמת

| קטגוריה | כלל | ערך |
|---------|------|-----|
| סינון | RSI | 50-75 |
| סינון | RVOL | ≥1.5x |
| סינון | שינוי יומי | 2%-10% |
| סינון | BB Width | <0.15 |
| סינון | מרחק משיא | ≥95% |
| סינון | EMA | Price>EMA20>EMA50 |
| מסחר | פוזיציה | $2,000 |
| מסחר | מקסימום | 3 מניות/יום |
| יציאה | Stop Loss | -3% |
| יציאה | TP1 | +5% (50%) |
| יציאה | TP2 | +10% (100%) |
| יציאה | Time Stop | 48h, <1% |
| למידה | WIN | ≥+10% |
| למידה | LOSS | ≤-5% |
| למידה | Learning Rate | 0.02 |

---

*תאריך: ינואר 2026*
