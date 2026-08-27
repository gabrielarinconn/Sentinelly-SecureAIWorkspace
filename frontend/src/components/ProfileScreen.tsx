import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nContext";
import { Avatar } from "./Avatar";

/** Pantalla de perfil de solo lectura, abierta al hacer clic en el propio avatar (Sidebar).
 * No edita nombre/cargo/estado — eso requeriría un endpoint de actualización que no existe
 * hoy (GET /users/me es de solo lectura); esta pantalla solo muestra los datos ya cargados en
 * AuthContext y agrega cerrar sesión, que es lo que se pidió. */
export function ProfileScreen({ onBack }: { onBack: () => void }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();

  return (
    <div className="profile-screen">
      <button className="profile-back-button" onClick={onBack}>
        ← {t("profile.back")}
      </button>
      <div className="profile-card">
        <div className="profile-identity">
          <Avatar initial={user?.full_name?.charAt(0)} size="lg" />
          <div>
            <h1>{user?.full_name}</h1>
            <p className="profile-role">{user?.role_title}</p>
          </div>
        </div>

        <div className="profile-field">
          <label>{t("profile.email")}</label>
          <div className="profile-field-value">{user?.email}</div>
        </div>

        <button className="profile-logout-button" onClick={() => void logout()}>
          {t("sidebar.logout")}
        </button>
      </div>
    </div>
  );
}
