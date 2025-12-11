# דוח סיכום EDA לנתוני גנים

## קבצים וחלוקות
- `train.csv`: 22593 שורות
- `validation.csv`: 4577 שורות
- `test.csv`: 8326 שורות
- סה"כ: 35496 שורות, 10 מחלקות

## התפלגות מחלקות
- המחלקות הדומיננטיות: PSEUDO (16153), BIOLOGICAL_REGION (10974), ncRNA (3907)
- המחלקות הדלילות ביותר: rRNA (357), snRNA (205), scRNA (4)
- קבצים: `label_counts_per_split.png`, `label_counts_overall.png`

## אורכי רצפים
- סטטיסטיקות: min=2, median=295.0, mean=361.4657144466982, p95=916.0, p99=980.0, max=1000
- התפלגות: `seq_length_distribution.png` (ציר Y לוגרי)
- השוואה לפי מחלקה (6 הנפוצות): `seq_length_by_label.png`

## חפיפות אפשריות בין פיצולים
- מזהי NCBI משותפים לכל הפיצולים: 882
- מזהי NCBI חופפים בזוגות: train-validation: 4577, train-test: 7140, validation-test: 882
- רצפים נקיים משותפים לכל הפיצולים: 903
- רצפים חופפים בזוגות: train-validation: 4577, train-test: 7204, validation-test: 903

## מסקנות קצרות
- אי־איזון מחלקות בולט (PSEUDO, BIOLOGICAL_REGION רוב הדאטה).
- רצפים באורכים מגוונים מאוד; ערך p95≈916 מציע לקבוע max_len מתון.
- קיימות חפיפות בין פיצולים (geneID/רצפים); לשקול פיצול מחדש כדי למנוע דליפה.)
- מחלקות קטנות מאוד (scRNA/snRNA/rRNA/tRNA/OTHER) ידרשו weighting/oversampling.)