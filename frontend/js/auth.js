/**
 * Módulo de autenticación con Google (vía Supabase Auth).
 * Expone: window.auth.{loginWithGoogle, logout, getSession, onAuthStateChange, getAccessToken}
 */
(function () {
  const auth = {
    /**
     * Inicia el flujo OAuth con Google.
     * Redirige al usuario a la pantalla de consentimiento.
     */
    async loginWithGoogle() {
      try {
        const { data, error } =
          await window.supabaseClient.auth.signInWithOAuth({
            provider: "google",
            options: {
              redirectTo: "https://mapahamburguesa-lf3i.vercel.app"
            }
          });

        if (error) throw error;
        // El browser redirige solo a data.url
      } catch (err) {
        console.error("Error en loginWithGoogle:", err);
        alert("No se pudo iniciar sesión con Google. Intentá de nuevo.");
      }
    },

    /**
     * Cierra la sesión.
     */
    async logout() {
      try {
        const { error } = await window.supabaseClient.auth.signOut();
        if (error) throw error;
        window.location.reload();
      } catch (err) {
        console.error("Error en logout:", err);
        alert("No se pudo cerrar la sesión.");
      }
    },

    /**
     * Devuelve la sesión actual (o null si no hay).
     */
    async getSession() {
      try {
        const { data, error } =
          await window.supabaseClient.auth.getSession();
        if (error) throw error;
        return data.session || null;
      } catch (err) {
        console.error("Error getSession:", err);
        return null;
      }
    },

    /**
     * Devuelve el access_token de la sesión actual (o null).
     */
    async getAccessToken() {
      const session = await this.getSession();
      return session?.access_token || null;
    },

    /**
     * Devuelve el user logueado con datos del profile.
     */
    async getCurrentUser() {
      const session = await this.getSession();
      if (!session?.user) return null;

      try {
        const { data: profile, error } = await window.supabaseClient
          .from("profiles")
          .select("*")
          .eq("id", session.user.id)
          .single();

        if (error && error.code !== "PGRST116") {
          console.warn("Error trayendo profile:", error);
        }

        return {
          id: session.user.id,
          email: session.user.email,
          name: profile?.name || session.user.email.split("@")[0],
          avatar_url: profile?.avatar_url || null,
          role: profile?.role || "user",
          is_active: profile?.is_active !== false,
        };
      } catch (err) {
        console.error("Error getCurrentUser:", err);
        return null;
      }
    },

    /**
     * Suscripción a cambios de auth (login/logout).
     * Devuelve la función de unsubscribe.
     */
    onAuthStateChange(callback) {
      const { data } = window.supabaseClient.auth.onAuthStateChange(
        (event, session) => {
          callback(event, session);
        }
      );
      return () => data.subscription.unsubscribe();
    },

    /**
     * Devuelve true si el usuario es admin o moderator.
     */
    isModerator(user) {
      return user && (user.role === "admin" || user.role === "moderator");
    },

    isAdmin(user) {
      return user && user.role === "admin";
    },
  };

  window.auth = auth;
})();
