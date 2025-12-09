import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Textfield, Heading, Paragraph } from "@digdir/designsystemet-react";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      navigate("/search");
    } catch (err) {
      setError(t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: "flex", 
      flexDirection: "column", 
      alignItems: "center", 
      justifyContent: "center", 
      minHeight: "100vh",
      padding: "2rem"
    }}>
      <div style={{ width: "100%", maxWidth: "400px" }}>
        <Heading level={1} size="lg" style={{ marginBottom: "1.5rem" }}>
          {t("auth.login")}
        </Heading>
        
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <Textfield
            label={t("auth.email")}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          
          <Textfield
            label={t("auth.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          
          {error && (
            <Paragraph size="sm" style={{ color: "red" }}>
              {error}
            </Paragraph>
          )}
          
          <Button type="submit" disabled={loading}>
            {loading ? t("common.loading") : t("auth.loginButton")}
          </Button>
        </form>
        
        <Paragraph size="sm" style={{ marginTop: "1rem", marginBottom: "0.5rem" }}>
          {t("auth.noAccount")}{" "}
          <Link to="/register">{t("auth.register")}</Link>
        </Paragraph>
      </div>
    </div>
  );
}

