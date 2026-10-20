import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getWeeklyRecap } from "../api/recap.js";
import { ui } from "../ui/ui.js";

export default function WeeklyRecapPage() {
  // Fetch weekly recap data
  const recapQuery = useQuery({
    queryKey: ["weekly-recap"],
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    queryFn: async () => {
      return getWeeklyRecap();
    },
  });
  // Destructure React Query result for easier usage
  const { data = {}, isLoading, error } = recapQuery;
  if (isLoading) {
    return (
      <div style={{ padding: "24px", maxWidth: "1000px", margin: "0 auto" }}>
        <h1 style={{ marginTop: 0, marginBottom: "8px" }}>
          Recapul tău săptămânal
        </h1>
        <p style={{ opacity: 0.8, marginTop: 0, marginBottom: "32px" }}>
          Rezumatul activității tale din ultima săptămână
        </p>
        <p>Se încarcă recapul...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px", maxWidth: "1000px", margin: "0 auto" }}>
        <h1 style={{ marginTop: 0, marginBottom: "8px" }}>
          Recapul tău săptămânal
        </h1>
        <p style={{ opacity: 0.8, marginTop: 0, marginBottom: "32px" }}>
          Rezumatul activității tale din ultima săptămână
        </p>
        <p style={ui.errorText}>{error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", maxWidth: "1000px", margin: "0 auto" }}>
      <h1 style={{ marginTop: 0, marginBottom: "8px" }}>
        Recapul tău săptămânal
      </h1>
      <p style={{ opacity: 0.8, marginTop: 0, marginBottom: "32px" }}>
        Rezumatul activității tale din ultima săptămână
      </p>

      {/* Top Listens Section */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>
          🎵 Top albume ascultate
        </h2>
        {data.top_listens && data.top_listens.length > 0 ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: "16px",
            }}
          >
            {data.top_listens.map((album, idx) => (
              <Link
                key={album.id}
                to={album.slug ? `/albums/${album.slug}` : "/albums"}
                style={{ ...ui.card, color: "inherit", textDecoration: "none" }}
              >
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: 700,
                    marginBottom: "8px",
                    opacity: 0.8,
                  }}
                >
                  #{idx + 1}
                </div>
                <div style={{ fontWeight: 700 }}>{album.title}</div>
                <div style={{ marginTop: "4px", opacity: 0.8 }}>
                  {album.artist}
                </div>
                <div style={{ marginTop: "8px", fontSize: "14px" }}>
                  <strong>{album.listen_count}</strong> ascultări
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p style={{ opacity: 0.75 }}>Nu ai ascultări în această săptămână.</p>
        )}
      </section>

      {/* Streak Section */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>🔥 Streak</h2>
        <div style={{ ...ui.card, fontSize: "16px", padding: "20px" }}>
          <div style={{ fontSize: "32px", fontWeight: 700, color: "#ff6b6b" }}>
            {data.streak || 0} zile
          </div>
          <p style={{ marginTop: "8px", opacity: 0.75 }}>
            Zilele consecutive în care ai fost activ
          </p>
        </div>
      </section>

      {/* New Friends Section */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>
          👥 Prieteni noi ({data.new_friends_count || 0})
        </h2>
        {data.new_friends && data.new_friends.length > 0 ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
              gap: "12px",
            }}
          >
            {data.new_friends.map((friend) => (
              <Link
                key={friend.id}
                to={`/users/${friend.username}`}
                style={{
                  ...ui.card,
                  color: "inherit",
                  textDecoration: "none",
                  textAlign: "center",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "14px" }}>
                  {friend.first_name || friend.username}
                </div>
                <div
                  style={{ marginTop: "4px", opacity: 0.75, fontSize: "12px" }}
                >
                  @{friend.username}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p style={{ opacity: 0.75 }}>
            Nu ai acceptat cereri de prietenie în această săptămână.
          </p>
        )}
      </section>

      {/* Top Reviews Section */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>
          ⭐ Review-uri cu cel mai mare engagement
        </h2>
        {data.top_reviews && data.top_reviews.length > 0 ? (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {data.top_reviews.map((review) => (
              <Link
                key={review.id}
                to={
                  review.album_slug ? `/albums/${review.album_slug}` : "/albums"
                }
                style={{ ...ui.card, color: "inherit", textDecoration: "none" }}
              >
                <div
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700 }}>{review.album_title}</div>
                    <div style={{ opacity: 0.75, marginTop: "4px" }}>
                      {review.artist_name}
                    </div>
                    <div
                      style={{
                        marginTop: "8px",
                        fontSize: "13px",
                        opacity: 0.8,
                      }}
                    >
                      {review.text}
                    </div>
                    <div
                      style={{
                        marginTop: "8px",
                        fontSize: "12px",
                        opacity: 0.7,
                      }}
                    >
                      Recenzie de{" "}
                      <Link
                        to={`/users/${review.username}`}
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: "#007bff", textDecoration: "none" }}
                      >
                        @{review.username}
                      </Link>
                    </div>
                  </div>
                  <div
                    style={{
                      marginLeft: "16px",
                      textAlign: "right",
                      fontSize: "12px",
                    }}
                  >
                    <div style={{ fontSize: "18px", fontWeight: 700 }}>
                      {review.rating || "N/A"}⭐
                    </div>
                    <div style={{ marginTop: "8px", opacity: 0.75 }}>
                      👍 {review.likes_count}
                    </div>
                    <div style={{ marginTop: "4px", opacity: 0.75 }}>
                      💬 {review.comments_count}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p style={{ opacity: 0.75 }}>
            Prietenii tăi nu au scris review-uri cu engagement ridicat în
            această săptămână.
          </p>
        )}
      </section>

      {data.weekly_challenges?.previous_week_recap ? (
        <section style={{ marginBottom: "32px" }}>
          <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>
            🎯 Recap provocări
          </h2>
          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              background: "rgba(17, 24, 39, 0.04)",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: "8px" }}>
              {data.weekly_challenges.previous_week_recap.week_start} -{" "}
              {data.weekly_challenges.previous_week_recap.week_end}
            </div>
            <div style={{ marginBottom: "12px", opacity: 0.85 }}>
              Completate:{" "}
              {data.weekly_challenges.previous_week_recap.completed_count ?? 0}/
              {data.weekly_challenges.previous_week_recap.total_count ?? 0}
            </div>
            <div style={{ display: "grid", gap: "12px" }}>
              <div>
                <div style={{ fontWeight: 700, marginBottom: "6px" }}>
                  Finalizate
                </div>
                {data.weekly_challenges.previous_week_recap.completed_challenges
                  ?.length ? (
                  <ul style={{ margin: 0, paddingLeft: "18px" }}>
                    {data.weekly_challenges.previous_week_recap.completed_challenges.map(
                      (challenge) => (
                        <li key={challenge.key}>
                          {challenge.title} ({challenge.progress}/
                          {challenge.target})
                        </li>
                      ),
                    )}
                  </ul>
                ) : (
                  <p style={{ margin: 0, opacity: 0.8 }}>
                    Nu ai finalizat nicio provocare săptămâna trecută.
                  </p>
                )}
              </div>
              <div>
                <div style={{ fontWeight: 700, marginBottom: "6px" }}>
                  Nefinalizate
                </div>
                {data.weekly_challenges.previous_week_recap
                  .incomplete_challenges?.length ? (
                  <ul style={{ margin: 0, paddingLeft: "18px" }}>
                    {data.weekly_challenges.previous_week_recap.incomplete_challenges.map(
                      (challenge) => (
                        <li key={challenge.key}>
                          {challenge.title} ({challenge.progress}/
                          {challenge.target})
                        </li>
                      ),
                    )}
                  </ul>
                ) : (
                  <p style={{ margin: 0, opacity: 0.8 }}>
                    Toate provocările au fost finalizate.
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <section style={{ marginTop: "32px" }}>
        <div style={{ ...ui.card, padding: "12px" }}>
          <p style={{ margin: 0, fontSize: "12px", opacity: 0.75 }}>
            Period:{" "}
            {data.week_from
              ? new Date(data.week_from).toLocaleDateString("ro-RO")
              : "N/A"}{" "}
            -{" "}
            {data.week_to
              ? new Date(data.week_to).toLocaleDateString("ro-RO")
              : "N/A"}
          </p>
        </div>
      </section>
    </div>
  );
}
