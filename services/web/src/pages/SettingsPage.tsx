import { useState, useEffect } from "react";
import {
  User,
  Lock,
  Mail,
  Building2,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { api, getUsername } from "../api/client";

interface UserProfile {
  username: string;
  user_id: string;
  email: string;
  company_domain: string;
  role: string;
}

export function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [email, setEmail] = useState("");
  const [companyDomain, setCompanyDomain] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [changingPw, setChangingPw] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const resp = await api.get<UserProfile>("/api/v1/auth/me");
      setProfile(resp.data);
      setEmail(resp.data.email || "");
      setCompanyDomain(resp.data.company_domain || "");
    } catch {
      /* ignore */
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.put("/api/v1/auth/profile", {
        email,
        company_domain: companyDomain,
      });
      setMessage({ type: "success", text: "Profile updated" });
      loadProfile();
    } catch {
      setMessage({ type: "error", text: "Failed to update profile" });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match" });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({
        type: "error",
        text: "New password must be at least 6 characters",
      });
      return;
    }
    setChangingPw(true);
    setMessage(null);
    try {
      await api.post("/api/v1/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage({ type: "success", text: "Password changed successfully" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg =
        (err as Error)?.message || "Failed to change password";
      setMessage({ type: "error", text: msg });
    } finally {
      setChangingPw(false);
    }
  };

  return (
    <div className="h-full overflow-auto p-6 space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Account Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your account, profile, and security.
        </p>
      </div>

      {message && (
        <div
          className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
            message.type === "success"
              ? "bg-green-500/10 border border-green-500/20 text-green-400"
              : "bg-destructive/10 border border-destructive/20 text-destructive"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          {message.text}
        </div>
      )}

      {/* Profile section */}
      <div className="space-y-4 border border-border rounded-xl p-5">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <User className="h-5 w-5 text-primary" />
          Profile
        </h2>

        <div className="grid gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">
              Username
            </label>
            <div className="mt-1 px-4 py-2.5 rounded-lg bg-muted/30 text-sm">
              {getUsername()}
            </div>
          </div>

          {profile?.role && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Role
              </label>
              <div className="mt-1 px-4 py-2.5 rounded-lg bg-muted/30 text-sm capitalize">
                {profile.role}
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5" />
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="mt-1 w-full px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
            <p className="text-[11px] text-muted-foreground mt-1">
              Work emails auto-detect your company domain for Canon knowledge
              sharing.
            </p>
          </div>

          <div>
            <label className="text-sm font-medium flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5" />
              Company domain
            </label>
            <input
              type="text"
              value={companyDomain}
              onChange={(e) => setCompanyDomain(e.target.value)}
              placeholder="company.com"
              className="mt-1 w-full px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
          </div>

          <button
            onClick={handleSaveProfile}
            disabled={saving}
            className="self-start flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save profile
          </button>
        </div>
      </div>

      {/* Change password section */}
      <div className="space-y-4 border border-border rounded-xl p-5">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Lock className="h-5 w-5 text-primary" />
          Change password
        </h2>

        <div className="grid gap-4">
          <div>
            <label className="text-sm font-medium">Current password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="mt-1 w-full px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
          </div>

          <div>
            <label className="text-sm font-medium">New password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Min 6 characters"
              className="mt-1 w-full px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Confirm new password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 w-full px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            />
          </div>

          <button
            onClick={handleChangePassword}
            disabled={changingPw || !currentPassword || !newPassword}
            className="self-start flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all"
          >
            {changingPw && <Loader2 className="h-4 w-4 animate-spin" />}
            Change password
          </button>
        </div>
      </div>

      {/* Account info */}
      {profile && (
        <div className="text-[11px] text-muted-foreground space-y-1">
          <p>User ID: {profile.user_id}</p>
        </div>
      )}
    </div>
  );
}
