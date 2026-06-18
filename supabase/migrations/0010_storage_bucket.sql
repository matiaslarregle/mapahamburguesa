-- =============================================================================
-- 0010_storage_bucket.sql
-- Crear bucket público 'place-photos' con límite de 8MB por archivo.
-- =============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'place-photos',
    'place-photos',
    true,
    8388608,  -- 8 MB
    ARRAY['image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO NOTHING;

-- ====================== POLICIES DEL BUCKET ======================
-- Cualquiera puede VER (bucket público)
DROP POLICY IF EXISTS "Public read place-photos" ON storage.objects;
CREATE POLICY "Public read place-photos"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'place-photos');

-- Solo autenticados pueden SUBIR
DROP POLICY IF EXISTS "Auth users can upload to place-photos" ON storage.objects;
CREATE POLICY "Auth users can upload to place-photos"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'place-photos'
        AND auth.role() = 'authenticated'
    );

-- Solo el dueño o admin puede BORRAR
DROP POLICY IF EXISTS "Owner or admin can delete from place-photos" ON storage.objects;
CREATE POLICY "Owner or admin can delete from place-photos"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'place-photos'
        AND (
            auth.uid() = owner
            OR EXISTS (
                SELECT 1 FROM public.profiles
                WHERE id = auth.uid() AND role = 'admin'
            )
        )
    );
