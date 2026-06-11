-- Supabase SQL Editor da shu kodni RUN qiling

ALTER TABLE foydalanuvchilar 
  ADD COLUMN IF NOT EXISTS balans INTEGER DEFAULT 30000,
  ADD COLUMN IF NOT EXISTS referral_by TEXT;

ALTER TABLE ustaxonalar
  ADD COLUMN IF NOT EXISTS aktiv BOOLEAN DEFAULT true;

CREATE TABLE IF NOT EXISTS balans_tarixi (
  id SERIAL PRIMARY KEY,
  foydalanuvchi_id TEXT,
  tur TEXT,
  miqdor INTEGER,
  izoh TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bron_narxlar (
  id SERIAL PRIMARY KEY,
  xizmat_turi TEXT UNIQUE NOT NULL,
  narx INTEGER NOT NULL
);

INSERT INTO bron_narxlar (xizmat_turi, narx) VALUES
  ('Moy almashtirish', 2000),
  ('Diagnostika', 3000),
  ('Shina almashtirish', 2500),
  ('Elektr tizimi', 5000),
  ('Kuzov ta''miri', 8000),
  ('Dvigatel ta''miri', 12000),
  ('Bo''yash', 15000)
ON CONFLICT (xizmat_turi) DO UPDATE SET narx = EXCLUDED.narx;

ALTER TABLE balans_tarixi ENABLE ROW LEVEL SECURITY;
ALTER TABLE bron_narxlar ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_all_bt" ON balans_tarixi FOR ALL USING (true);
CREATE POLICY "public_read_bn" ON bron_narxlar FOR SELECT USING (true);
CREATE POLICY "public_all_bn" ON bron_narxlar FOR ALL USING (true);
