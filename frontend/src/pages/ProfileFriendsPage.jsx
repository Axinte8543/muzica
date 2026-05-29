import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import PaginationControls from "../components/PaginationControls.jsx";
import {
  acceptFriendRequest,
  getFriendsList,
  rejectFriendRequest,
} from "../api/friends.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ProfileFriendsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [friends, setFriends] = useState([]);
  const [friendsPageInfo, setFriendsPageInfo] = useState({
    count: 0,
    next: null,
    previous: null,
  });
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [friendsPage, setFriendsPage] = useState(1);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);

  const friendsCountLabel = useMemo(() => {
    if (isLoading) return "";
    return ` (${Number(friendsPageInfo.count) || 0})`;
  }, [friendsPageInfo.count, isLoading]);

  const friendsTotalPages = useMemo(() => {
    return Math.max(1, Math.ceil((Number(friendsPageInfo.count) || 0) / 10));
  }, [friendsPageInfo.count]);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const load = useCallback(async () => {
    if (!canLoad) {
      setFriends([]);
      setFriendsPageInfo({ count: 0, next: null, previous: null });
      setIncoming([]);
      setOutgoing([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await getFriendsList({
        baseUrl,
        accessToken,
        page: friendsPage,
      });
      const nextFriends = Array.isArray(data?.friends?.results)
        ? data.friends.results
        : [];
      setFriends(nextFriends);
      setFriendsPageInfo({
        count: Number(data?.friends?.count) || nextFriends.length,
        next: data?.friends?.next || null,
        previous: data?.friends?.previous || null,
      });
      setIncoming(Array.isArray(data?.incoming) ? data.incoming : []);
      setOutgoing(Array.isArray(data?.outgoing) ? data.outgoing : []);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut încărca prietenii.");
      setFriends([]);
      setFriendsPageInfo({ count: 0, next: null, previous: null });
      setIncoming([]);
      setOutgoing([]);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, baseUrl, canLoad, friendsPage, logout]);

  useEffect(() => {
    if (!canLoad) return;
    void load();
  }, [canLoad, load]);

  useEffect(() => {
    setFriendsPage((prev) => Math.min(prev, friendsTotalPages));
  }, [friendsTotalPages]);

  async function handleAccept(requestId) {
    if (!requestId) return;
    setActionError(null);

    try {
      await acceptFriendRequest({ baseUrl, accessToken, requestId });
      await load();
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setActionError("Nu am putut accepta cererea.");
    }
  }

  async function handleReject(requestId) {
    if (!requestId) return;
    setActionError(null);

    try {
      await rejectFriendRequest({ baseUrl, accessToken, requestId });
      await load();
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setActionError("Nu am putut respinge cererea.");
    }
  }

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={ui.container}>
          <h1 style={{ marginTop: 0 }}>Prieteni</h1>
          <p>Trebuie să fii logat ca să vezi prietenii.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div>
        <ProfileNav />
        <div style={ui.container}>
          <h1 style={{ marginTop: 0 }}>Prieteni</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Prieteni</h1>

        {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
        {error ? (
          <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
            {error}
          </p>
        ) : null}
        {actionError ? (
          <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
            {actionError}
          </p>
        ) : null}

        <section style={{ marginTop: "18px" }}>
          <h2 style={{ margin: 0 }}>Lista de prieteni{friendsCountLabel}</h2>

          {!isLoading && !error ? (
            <div style={{ ...ui.card, marginTop: "12px" }}>
              {friends.length ? (
                <ul style={{ paddingLeft: "18px", margin: 0 }}>
                  {friends.map((f) => {
                    const username = String(f?.username || "").trim();
                    const id = f?.id;
                    if (!username || !id) return null;

                    return (
                      <li key={id} style={{ margin: "6px 0" }}>
                        <Link to={`/users/${encodeURIComponent(username)}`}>
                          {username}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <div style={{ opacity: 0.9 }}>Nu ai prieteni încă.</div>
              )}
            </div>
          ) : null}
          <PaginationControls
            page={friendsPage}
            totalPages={friendsTotalPages}
            totalCount={friendsPageInfo.count}
            onPrev={() => setFriendsPage((prev) => Math.max(1, prev - 1))}
            onNext={() =>
              setFriendsPage((prev) => Math.min(friendsTotalPages, prev + 1))
            }
          />
        </section>

        <section style={{ marginTop: "22px" }}>
          <h2 style={{ margin: 0 }}>Cereri primite</h2>

          {!isLoading && !error ? (
            <div style={{ ...ui.card, marginTop: "12px" }}>
              {incoming.length ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {incoming.map((fr) => {
                    const sender = String(fr?.sender_username || "").trim();
                    const requestId = fr?.id;
                    if (!sender || !requestId) return null;

                    return (
                      <div
                        key={requestId}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "12px",
                        }}
                      >
                        <div style={{ opacity: 0.95 }}>
                          <Link to={`/users/${encodeURIComponent(sender)}`}>
                            {sender}
                          </Link>{" "}
                          vrea să fie prieten cu tine.
                        </div>

                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            type="button"
                            style={ui.button}
                            onClick={() => handleAccept(requestId)}
                          >
                            Acceptă
                          </button>
                          <button
                            type="button"
                            style={ui.button}
                            onClick={() => handleReject(requestId)}
                          >
                            Respinge
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ opacity: 0.9 }}>Nu ai cereri primite.</div>
              )}
            </div>
          ) : null}
        </section>

        <section style={{ marginTop: "22px" }}>
          <h2 style={{ margin: 0 }}>Cereri trimise</h2>

          {!isLoading && !error ? (
            <div style={{ ...ui.card, marginTop: "12px" }}>
              {outgoing.length ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  {outgoing.map((fr) => {
                    const receiver = String(fr?.receiver_username || "").trim();
                    const requestId = fr?.id;
                    if (!receiver || !requestId) return null;

                    return (
                      <div key={requestId} style={{ opacity: 0.95 }}>
                        Ai trimis o cerere către{" "}
                        <Link to={`/users/${encodeURIComponent(receiver)}`}>
                          {receiver}
                        </Link>
                        .
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ opacity: 0.9 }}>Nu ai cereri trimise.</div>
              )}
            </div>
          ) : null}
        </section>

        {!isLoading && !error ? (
          <div style={{ marginTop: "16px" }}>
            <button type="button" style={ui.button} onClick={load}>
              Reîncarcă
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
