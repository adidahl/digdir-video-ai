import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Select } from "@digdir/designsystemet-react";
import { useAuth } from "../../hooks/useAuth";
import { Role } from "../../types/auth";

export default function Header() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const brandColor = "#1e2b3c";
  const brandStyle = { backgroundColor: brandColor, color: "#fff", borderColor: brandColor };
  const navButtonProps = {
    variant: "secondary" as const,
    size: "sm" as const,
    style: { ...brandStyle, textDecoration: "none" },
  };

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("language", lang);
  };

  return (
    <header style={{ padding: "1rem", borderBottom: "1px solid #ccc", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <Link to="/search" style={{ textDecoration: "none", color: "inherit", display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
          <img
            src="https://www.digdir.no/profiles/sogn/themes/sogn_theme/img/logo/logo_sogn.svg?t6z6tt"
            alt="DigDir logo"
            style={{ height: "32px" }}
          />
        </Link>
      </div>
      
      {user && (
        <nav style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <Link to="/search" style={{ textDecoration: "none" }}>
            <Button {...navButtonProps}>{t("nav.search")}</Button>
          </Link>
          {(user.role === Role.ORG_ADMIN || user.role === Role.SUPER_ADMIN) && (
            <Link to="/admin" style={{ textDecoration: "none" }}>
              <Button {...navButtonProps}>{t("nav.admin")}</Button>
            </Link>
          )}
          <Link to="/settings" style={{ textDecoration: "none" }}>
            <Button {...navButtonProps}>{t("nav.profile")}</Button>
          </Link>
          
          <Select 
            size="sm"
            value={i18n.language} 
            onChange={(e) => changeLanguage(e.target.value)}
            style={brandStyle}
          >
            <option value="en">English</option>
            <option value="nb">Norsk Bokmål</option>
            <option value="nn">Norsk Nynorsk</option>
          </Select>
          
          <Button 
            variant="secondary" 
            size="sm" 
            onClick={logout}
            style={{ ...brandStyle, minWidth: "110px" }}
          >
            {t("nav.logout")}
          </Button>
        </nav>
      )}
    </header>
  );
}

