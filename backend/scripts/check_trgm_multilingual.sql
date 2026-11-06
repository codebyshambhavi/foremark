-- FOREMARK: does pg_trgm behave usefully on English, Hinglish (Latin script) and Hindi (Devanagari)?
--
-- WHY: the Safety Memory Engine may use pg_trgm text similarity as ONE signal among several.
-- pg_trgm's notion of a "word character" depends on the database's LC_CTYPE, so results can differ
-- between machines. Run this against the database you will actually use and read the numbers.
--
-- Run (Docker Compose database):
--   docker compose exec -T db psql -U foremark -d foremark < backend/scripts/check_trgm_multilingual.sql
--
-- All sample sentences are SYNTHETIC illustrations, not real reports.
-- No thresholds are applied here on purpose: this script only shows what the extension computes.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

\echo '=== Database locale (LC_CTYPE drives pg_trgm word-character handling) ==='
SELECT datname, datcollate, datctype, pg_encoding_to_char(encoding) AS encoding
FROM pg_database WHERE datname = current_database();

\echo ''
\echo '=== Trigram extraction for single words (empty or fragmentary output = Devanagari is being split or dropped) ==='
SELECT 'English'  AS script, 'water' AS word,  show_trgm('water')  AS trigrams
UNION ALL SELECT 'Hinglish', 'paani',  show_trgm('paani')
UNION ALL SELECT 'Devanagari', 'पानी',  show_trgm('पानी')
UNION ALL SELECT 'Devanagari', 'बेसमेंट', show_trgm('बेसमेंट');

\echo ''
\echo '=== Pairwise similarity (0 = no shared trigrams, 1 = identical). "expect" is the human judgement. ==='
WITH pairs(label, expect, a, b) AS (VALUES
  ('EN same hazard, reworded',       'similar',
     'Water collected on floor near electrical panel room, Basement 2',
     'Water accumulation near electrical panel room in Basement Level 2'),
  ('EN same place, different hazard','different',
     'Water collected near electrical panel room',
     'Scaffold plank missing on level 4'),
  ('Hinglish same hazard, spelling variants','similar',
     'basement me electrical room ke paas pani jama hai',
     'basement mein electrical room ke paas paani bhar gaya hai'),
  ('Hinglish different hazards',     'different',
     'basement me pani jama hai',
     'terrace pe scaffold ka plank toota hua hai'),
  ('Hindi same hazard, reworded',    'similar',
     'बेसमेंट में इलेक्ट्रिकल रूम के पास पानी जमा है',
     'बेसमेंट में इलेक्ट्रिकल रूम के पास पानी भरा हुआ है'),
  ('Hindi different hazards',        'different',
     'बेसमेंट में पानी जमा है',
     'छत पर स्कैफोल्ड का तख्ता टूटा है'),
  ('Cross-script: Devanagari vs Latin (same meaning)', 'similar in meaning, expected ~0 for trigrams',
     'पानी जमा है',
     'pani jama hai'),
  ('Cross-language: English vs Hindi (same meaning)',  'similar in meaning, expected ~0 for trigrams',
     'Water near electrical room',
     'इलेक्ट्रिकल रूम के पास पानी')
)
SELECT label,
       expect,
       round(similarity(a, b)::numeric, 3)          AS trgm_similarity,
       round(word_similarity(a, b)::numeric, 3)     AS word_similarity,
       cardinality(show_trgm(a))                    AS trgms_a,
       cardinality(show_trgm(b))                    AS trgms_b
FROM pairs;
