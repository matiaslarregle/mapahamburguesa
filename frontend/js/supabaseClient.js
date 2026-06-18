/**
 * Cliente Supabase para el frontend.
 * Solo usa la ANON_KEY (nunca la service_role).
 * Se carga como script global <script src="js/supabaseClient.js"></script>
 * y deja window.supabaseClient disponible para los demás módulos.
 */

// ⚠️ REEMPLAZAR con tus credenciales reales de Supabase
const SUPABASE_URL = "https://hohfsfpauvhkmeuhvqgy.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvaGZzZnBhdXZoa21ldWh2cWd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NDI2NTMsImV4cCI6MjA5NzMxODY1M30.IZSWD5gIHfy7W9WV4nmob-6AYf9HP8Q1uJL5Y7ex3FA ";

// Esperar a que la SDK de Supabase esté disponible (cargada por CDN antes)
(function initSupabase() {
  if (typeof window.supabase === "undefined") {
    console.error(
      "Supabase SDK no cargada. Asegurate de incluir el <script> de CDN antes de supabaseClient.js"
    );
    return;
  }

  try {
    const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    window.supabaseClient = client;
    console.log("✅ Supabase client inicializado");
  } catch (err) {
    console.error("❌ Error inicializando Supabase:", err);
  }
})();
