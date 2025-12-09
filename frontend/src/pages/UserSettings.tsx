import { useTranslation } from "react-i18next";
import { Heading, Card } from "@digdir/designsystemet-react";
import Header from "../components/layout/Header";
import { useAuth } from "../hooks/useAuth";

export default function UserSettings() {
  const { t } = useTranslation();
  const { user } = useAuth();

  return (
    <div>
      <Header />
      
      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem" }}>
        <Heading level={1} size="lg" style={{ marginBottom: "1.5rem" }}>
          {t("nav.profile")}
        </Heading>
        
        {user && (
          <Card style={{ padding: "2rem" }}>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Name:</strong> {user.full_name}</p>
            <p><strong>Role:</strong> {user.role}</p>
            <p><strong>Organization ID:</strong> {user.organization_id || "N/A"}</p>
          </Card>
        )}
      </div>
    </div>
  );
}

