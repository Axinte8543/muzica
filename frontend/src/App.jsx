import { Suspense, lazy } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import "./App.css";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import ScrollRestoration from "./components/ScrollRestoration.jsx";
import { AuthProvider } from "./context/AuthProvider.jsx";
import { NoticeProvider } from "./context/NoticeProvider.jsx";

const HomePage = lazy(() => import("./pages/HomePage.jsx"));
const AlbumsPage = lazy(() => import("./pages/AlbumsPage.jsx"));
const AlbumPage = lazy(() => import("./pages/AlbumPage.jsx"));
const ArtistPage = lazy(() => import("./pages/ArtistPage.jsx"));
const SongPage = lazy(() => import("./pages/SongPage.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));
const RegisterPage = lazy(() => import("./pages/RegisterPage.jsx"));
const VerifyEmailPage = lazy(() => import("./pages/VerifyEmailPage.jsx"));
const ConfirmEmailChangePage = lazy(
  () => import("./pages/ConfirmEmailChangePage.jsx"),
);
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage.jsx"));
const SearchResultsPage = lazy(() => import("./pages/SearchResultsPage.jsx"));
const TopAlbumsPage = lazy(() => import("./pages/TopAlbumsPage.jsx"));
const ListsPage = lazy(() => import("./pages/ListsPage.jsx"));
const MyListsPage = lazy(() => import("./pages/MyListsPage.jsx"));
const PublicListPage = lazy(() => import("./pages/PublicListPage.jsx"));
const FollowedArtistsPage = lazy(
  () => import("./pages/FollowedArtistsPage.jsx"),
);
const ProfileReviewsPage = lazy(() => import("./pages/ProfileReviewsPage.jsx"));
const ProfileRatingsPage = lazy(() => import("./pages/ProfileRatingsPage.jsx"));
const ProfileLikedAlbumsPage = lazy(
  () => import("./pages/ProfileLikedAlbumsPage.jsx"),
);
const ProfileStatsPage = lazy(() => import("./pages/ProfileStatsPage.jsx"));
const MyProfilePage = lazy(() => import("./pages/MyProfilePage.jsx"));
const ProfileTopPage = lazy(() => import("./pages/ProfileTopPage.jsx"));
const ProfileFriendsPage = lazy(() => import("./pages/ProfileFriendsPage.jsx"));
const ProfileListensPage = lazy(() => import("./pages/ProfileListensPage.jsx"));
const ProfileWantToListenPage = lazy(
  () => import("./pages/ProfileWantToListenPage.jsx"),
);
const ProfileWeeklyChallengesPage = lazy(
  () => import("./pages/ProfileWeeklyChallengesPage.jsx"),
);
const ProfileBadgesPage = lazy(() => import("./pages/ProfileBadgesPage.jsx"));
const ProfileAchievementsPage = lazy(
  () => import("./pages/ProfileAchievementsPage.jsx"),
);
const ProfileSuggestionsPage = lazy(
  () => import("./pages/ProfileSuggestionsPage.jsx"),
);
const SuggestPage = lazy(() => import("./pages/SuggestPage.jsx"));
const SimilarUsersPage = lazy(() => import("./pages/SimilarUsersPage.jsx"));
const UserProfilePage = lazy(() => import("./pages/UserProfilePage.jsx"));
const MusicStatsPage = lazy(() => import("./pages/MusicStatsPage.jsx"));
const ActivityPage = lazy(() => import("./pages/ActivityPage.jsx"));
const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"));
const RecommendationsPage = lazy(
  () => import("./pages/RecommendationsPage.jsx"),
);
const SimilarArtistsPage = lazy(() => import("./pages/SimilarArtistsPage.jsx"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage.jsx"));
const GenresPage = lazy(() => import("./pages/GenresPage.jsx"));
const StaticPage = lazy(() => import("./pages/StaticPage.jsx"));
const HighestRatedArtistsPage = lazy(
  () => import("./pages/HighestRatedArtistsPage.jsx"),
);
const RandomArtistPage = lazy(() => import("./pages/RandomArtistPage.jsx"));
const RandomAlbumPage = lazy(() => import("./pages/RandomAlbumPage.jsx"));
const ArtistReleasesPage = lazy(() => import("./pages/ArtistReleasesPage.jsx"));
const OnThisDayPage = lazy(() => import("./pages/OnThisDayPage.jsx"));
const UserUpdatesPage = lazy(() => import("./pages/UserUpdatesPage.jsx"));
const SiteUpdatesPage = lazy(() => import("./pages/SiteUpdatesPage.jsx"));
const NewsworthyPage = lazy(() => import("./pages/NewsworthyPage.jsx"));
const MessagesPage = lazy(() => import("./pages/MessagesPage.jsx"));
const CorrectionsPage = lazy(() => import("./pages/CorrectionsPage.jsx"));
const FAQPage = lazy(() => import("./pages/FAQPage.jsx"));
const ChangelogPage = lazy(() => import("./pages/ChangelogPage.jsx"));
const PrivacyPolicyPage = lazy(() => import("./pages/PrivacyPolicyPage.jsx"));
const TermsOfUsePage = lazy(() => import("./pages/TermsOfUsePage.jsx"));
const AdvertisingPage = lazy(() => import("./pages/AdvertisingPage.jsx"));
const ContactUsPage = lazy(() => import("./pages/ContactUsPage.jsx"));
const SubscribePage = lazy(() => import("./pages/SubscribePage.jsx"));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage.jsx"));
const WeeklyRecapPage = lazy(() => import("./pages/WeeklyRecapPage.jsx"));
const PrivacySettingsPage = lazy(
  () => import("./pages/PrivacySettingsPage.jsx"),
);
const MetadataSuggestionsPage = lazy(
  () => import("./pages/MetadataSuggestionsPage.jsx"),
);
const ExportDataPage = lazy(() => import("./pages/ExportDataPage.jsx"));

function AlbumPageRoute() {
  const { slug } = useParams();
  return <AlbumPage key={slug} slug={slug} />;
}

function ArtistPageRoute() {
  const { slug } = useParams();
  return <ArtistPage key={slug} slug={slug} />;
}

function ArtistReleasesPageRoute() {
  const { slug, section } = useParams();
  return (
    <ArtistReleasesPage
      key={`${slug}:${section}`}
      slug={slug}
      section={section}
    />
  );
}

function SongPageRoute() {
  const { slug } = useParams();
  return <SongPage key={slug} slug={slug} />;
}

function NavbarRoute() {
  const location = useLocation();
  return <Navbar key={location.pathname} />;
}

function RoutedContent() {
  const location = useLocation();

  return (
    <ErrorBoundary key={location.pathname}>
      <ScrollRestoration />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/albums" element={<AlbumsPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/recap/weekly" element={<WeeklyRecapPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route
            path="/confirm-email-change"
            element={<ConfirmEmailChangePage />}
          />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/search" element={<SearchResultsPage />} />
          <Route path="/top-albums" element={<TopAlbumsPage />} />
          <Route path="/lists" element={<ListsPage />} />
          <Route path="/my-lists" element={<MyListsPage />} />
          <Route path="/lists/public/:listId" element={<PublicListPage />} />
          <Route path="/following" element={<FollowedArtistsPage />} />
          <Route path="/profile/reviews" element={<ProfileReviewsPage />} />
          <Route path="/profile" element={<MyProfilePage />} />
          <Route path="/profile/listens" element={<ProfileListensPage />} />
          <Route
            path="/profile/want-to-listen"
            element={<ProfileWantToListenPage />}
          />
          <Route
            path="/profile/challenges/weekly"
            element={<ProfileWeeklyChallengesPage />}
          />
          <Route path="/profile/badges" element={<ProfileBadgesPage />} />
          <Route
            path="/profile/achievements"
            element={<ProfileAchievementsPage />}
          />
          <Route path="/profile/ratings" element={<ProfileRatingsPage />} />
          <Route
            path="/profile/liked-albums"
            element={<ProfileLikedAlbumsPage />}
          />
          <Route path="/profile/friends" element={<ProfileFriendsPage />} />
          <Route path="/profile/stats" element={<ProfileStatsPage />} />
          <Route path="/profile/privacy" element={<PrivacySettingsPage />} />
          <Route path="/profile/export" element={<ExportDataPage />} />
          <Route
            path="/profile/metadata-suggestions"
            element={<MetadataSuggestionsPage />}
          />

          <Route path="/profile/top" element={<ProfileTopPage />} />
          <Route
            path="/profile/suggestions"
            element={<ProfileSuggestionsPage />}
          />
          <Route path="/similar-users" element={<SimilarUsersPage />} />
          <Route path="/users/:username" element={<UserProfilePage />} />
          <Route path="/suggest" element={<SuggestPage />} />
          <Route path="/music-stats" element={<MusicStatsPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/similar-artists" element={<SimilarArtistsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/messages" element={<MessagesPage />} />
          <Route
            path="/romanian-songs"
            element={<Navigate to="/albums" replace />}
          />

          <Route path="/genres" element={<GenresPage />} />

          <Route path="/albums/random" element={<RandomAlbumPage />} />

          <Route
            path="/artists/highest-rated"
            element={<HighestRatedArtistsPage />}
          />
          <Route path="/artists/random" element={<RandomArtistPage />} />

          <Route path="/more/on-this-day" element={<OnThisDayPage />} />
          <Route path="/more/newsworthy" element={<NewsworthyPage />} />
          <Route path="/more/user-updates" element={<UserUpdatesPage />} />
          <Route path="/more/site-updates" element={<SiteUpdatesPage />} />
          <Route path="/more/corrections" element={<CorrectionsPage />} />

          <Route path="/site/faq" element={<FAQPage />} />
          <Route path="/site/changelog" element={<ChangelogPage />} />
          <Route path="/site/privacy" element={<PrivacyPolicyPage />} />
          <Route path="/site/terms" element={<TermsOfUsePage />} />
          <Route path="/site/advertising" element={<AdvertisingPage />} />
          <Route path="/site/contact" element={<ContactUsPage />} />
          <Route path="/site/subscribe" element={<SubscribePage />} />
          <Route path="/albums/:slug" element={<AlbumPageRoute />} />
          <Route path="/artists/:slug" element={<ArtistPageRoute />} />
          <Route
            path="/artists/:slug/releases/:section"
            element={<ArtistReleasesPageRoute />}
          />
          <Route path="/songs/:slug" element={<SongPageRoute />} />

          <Route path="*" element={<StaticPage title="Not Found" />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

function RouteFallback() {
  return <div style={{ padding: "16px" }}>Se încarcă...</div>;
}

function App() {
  return (
    <NoticeProvider>
      <AuthProvider>
        <div className="appShell">
          <div className="appShell__ambient appShell__ambient--one" />
          <div className="appShell__ambient appShell__ambient--two" />
          <div className="appShell__page">
            <header className="appShell__header">
              <NavbarRoute />
            </header>
            <main className="appShell__main">
              <h1
                style={{
                  position: "absolute",
                  width: "1px",
                  height: "1px",
                  padding: 0,
                  margin: "-1px",
                  overflow: "hidden",
                  clip: "rect(0, 0, 0, 0)",
                  clipPath: "inset(50%)",
                  whiteSpace: "nowrap",
                  border: 0,
                }}
              >
                roMusic
              </h1>
              <RoutedContent />
            </main>
            <Footer />
          </div>
        </div>
      </AuthProvider>
    </NoticeProvider>
  );
}

export default App;
