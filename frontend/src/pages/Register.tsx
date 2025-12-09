import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Textfield, Heading, Paragraph } from "@digdir/designsystemet-react";
import { authAPI } from "../api/auth";

export default function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await authAPI.register({ email, password, full_name: fullName, organization_name: organizationName });
      navigate("/login");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed");
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
          {t("auth.register")}
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
            minLength={8}
          />
          
          <Textfield
            label={t("auth.fullName")}
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          
          <Textfield
            label={t("auth.organizationName")}
            type="text"
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            required
          />
          
          {error && (
            <Paragraph size="sm" style={{ color: "red" }}>
              {error}
            </Paragraph>
          )}
          
          <Button type="submit" disabled={loading}>
            {loading ? t("common.loading") : t("auth.registerButton")}
          </Button>
        </form>
        
        <Paragraph size="sm" style={{ marginTop: "1rem", marginBottom: "0.5rem" }}>
          {t("auth.alreadyHaveAccount")}{" "}
          <Link to="/login">{t("auth.login")}</Link>
        </Paragraph>
      </div>
    </div>
  );
}

