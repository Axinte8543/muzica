from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from music.models import Album, Artist, Genre, Song


GENRE_ALIASES = {
    "hiphop": "Hip-Hop",
    "hip-hop": "Hip-Hop",
    "romanian-hiphop": "Romanian Hip-Hop",
    "romanian-hip-hop": "Romanian Hip-Hop",
    "rnb": "R&B",
    "r-b": "R&B",
    "romanian-rnb": "Romanian R&B",
    "romanian-r-b": "Romanian R&B",
    "drumnbass": "Drum and Bass",
    "drum-and-bass": "Drum and Bass",
    "dnb": "Drum and Bass",
    "old-school-hardcore": "Hardcore",
    "adult-alternative": "Alternative Rock",
    "romainian-pop": "Romanian Pop",
    "pop-latino": "Latin Pop",
    "rock-and-roll": "Rock and Roll",
    "synth-pop": "Synthpop",
    "synthpop": "Synthpop",
    "gothic-rock": "Gothic Rock",
    "gothic-metal": "Gothic Metal",
    "nu-metal": "Nu Metal",
    "progressive": "Progressive Rock",
    "progressive-rock": "Progressive Rock",
    "progressive-metal": "Progressive Metal",
    "progressive-electronic": "Progressive Electronic",
    "progressive-house": "Progressive House",
    "progressive-trance": "Progressive Trance",
    "progressive-psytrance": "Progressive Psytrance",
    "psychedelic-rock": "Psychedelic Rock",
    "stoner-rock": "Stoner Rock",
    "technical-death-metal": "Technical Death Metal",
    "melodic-death-metal": "Melodic Death Metal",
    "symphonic-black-metal": "Symphonic Black Metal",
    "folk-black-metal": "Folk Black Metal",
    "power-metal": "Power Metal",
    "power-thrash-metal": "Power Thrash Metal",
}


BAD_EXACT_SLUGS = {
    "00s",
    "12k",
    "1958",
    "3-stars",
    "40s",
    "50s",
    "60s",
    "70s",
    "90s",
    "90s-eurovision",
    "all",
    "american",
    "anca-badiu",
    "andra",
    "anozer",
    "antwerpen",
    "argentina",
    "armada",
    "ass",
    "australia",
    "austria",
    "austrian",
    "autist",
    "awsome",
    "band",
    "belgian",
    "born-in-iasi",
    "bosnian",
    "brazil",
    "brazilian",
    "british",
    "bucharest",
    "bucuresti",
    "bulgaria",
    "bulgarian",
    "cacat",
    "canadian",
    "cat-music",
    "check-later",
    "cheloo",
    "chicago",
    "chinese",
    "composers",
    "cuba",
    "cuban",
    "czech",
    "datejosamuly",
    "deezer",
    "dragos-udila",
    "ducu-bertzi",
    "dutch",
    "earthworm-jum",
    "eastern-europe",
    "eigen-makelij",
    "esc",
    "europe",
    "eurosonic-2012",
    "eurovision",
    "eurovision-song-contest",
    "facem-records",
    "female",
    "female-vocal",
    "female-vocalists",
    "finnish",
    "fiul-omului",
    "florin-chilian",
    "fresh",
    "funk-add-to-lidarr-batch-2",
    "funk_add_to_lidarr_batch_2",
    "game-ost",
    "garbage",
    "genial",
    "genius",
    "georgian",
    "german",
    "germany",
    "grasu-xxl",
    "guess-who",
    "hades-records",
    "high-quality-romanian-music",
    "holograf",
    "hop-shuoare",
    "iconic",
    "indonesian",
    "ioff-song-contest",
    "italian",
    "jamendo",
    "japanese",
    "jazz-mexicano",
    "junk",
    "korean",
    "la-familia",
    "lesser-known-yet-streamable-artists",
    "live",
    "love",
    "male-vocalist",
    "male-vocalists",
    "mc",
    "meerestief",
    "meh",
    "mexico",
    "moldova",
    "moldovan",
    "moldovian",
    "moosecore",
    "muist",
    "need-to-rate",
    "nice",
    "o-melodie-pentru-europa-2022",
    "ombladon",
    "pakistan",
    "panama",
    "paranoia-13",
    "paula-seling",
    "philosophical",
    "polish",
    "portland",
    "powerful",
    "proconsul",
    "radio",
    "rapper",
    "ro",
    "romaneasca",
    "romanesc",
    "romanian-male-vocalists",
    "romanian-music",
    "rumanian",
    "russian",
    "san-francisco",
    "seen-live",
    "seen-live-ro",
    "selectia-nationala",
    "serebro",
    "serious-range",
    "sexy",
    "sisu",
    "specii",
    "stefan-banica-jr",
    "strefa-rokendrola-wolna-od-angola",
    "suomi",
    "supreme-quality",
    "suriname",
    "talent",
    "the-undisputed-champion",
    "tiktok",
    "timisoara",
    "to-explore",
    "top-3-dj",
    "touhou",
    "trio",
    "tudor-chirila",
    "turkey",
    "turkish",
    "uddi",
    "uk",
    "ukrainian",
    "un-incontestabil-greu",
    "under-2000-listeners",
    "unicef",
    "vocalists",
    "x-factor",
}


BAD_CONTAINS = (
    "fuck",
    "cacat",
    "muzicadecacat",
    "muist",
)


ARTIST_OVERRIDES = {
    "Aerozen": {
        "set": ["trap", "Romanian Trap"],
    },
    "Alan": {
        "remove": ["j-pop", "c-pop"],
    },
    "Azteca": {
        "set": ["trap", "Romanian Trap", "Romanian Hip-Hop"],
    },
    "Aza": {
        "remove": ["ambient", "glitch"],
    },
    "Delia": {
        "remove": ["metal", "symphonic metal", "Gothic Rock", "Gothic Metal"],
        "add": ["dance-pop"],
    },
    "Ian": {
        "remove": ["heavy metal"],
        "add": ["Romanian Trap"],
    },
    "Jador": {
        "remove": ["Progressive Metal"],
    },
}


def _genre_for_name(name: str) -> Genre:
    slug = slugify(name)
    genre, created = Genre.objects.get_or_create(slug=slug, defaults={"name": name})
    if not created and genre.name != name:
        genre.name = name
        genre.save(update_fields=["name"])
    return genre


def _delete_if_unused(genre: Genre) -> bool:
    if genre.artists.exists() or genre.albums.exists() or genre.songs.exists():
        return False
    genre.delete()
    return True


def _move_relations(source: Genre, target: Genre) -> int:
    moved = 0
    for artist in source.artists.all():
        target.artists.add(artist)
        moved += 1
    for album in source.albums.all():
        target.albums.add(album)
        moved += 1
    for song in source.songs.all():
        target.songs.add(song)
        moved += 1

    source.artists.clear()
    source.albums.clear()
    source.songs.clear()
    return moved


class Command(BaseCommand):
    help = "Clean noisy Last.fm-style tags from artist genres and merge obvious duplicates."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving.")

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        removed_relations = 0
        removed_genres = 0
        merged_relations = 0
        merged_genres = 0
        override_changes = 0

        with transaction.atomic():
            for source_slug, target_name in GENRE_ALIASES.items():
                source = Genre.objects.filter(slug=source_slug).first()
                if source is None:
                    continue
                target = _genre_for_name(target_name)
                if source.id == target.id:
                    continue
                moved = (
                    source.artists.count()
                    + source.albums.count()
                    + source.songs.count()
                )
                if dry_run:
                    self.stdout.write(f"[dry-run] merge {source.name} -> {target.name}: relations={moved}")
                    merged_relations += moved
                    merged_genres += 1
                    continue
                merged_relations += _move_relations(source, target)
                if _delete_if_unused(source):
                    merged_genres += 1

            for genre in list(Genre.objects.order_by("slug")):
                slug = genre.slug
                name_key = genre.name.lower()
                should_remove = slug in BAD_EXACT_SLUGS or any(part in name_key for part in BAD_CONTAINS)
                if not should_remove:
                    continue

                relations = genre.artists.count()
                if dry_run:
                    self.stdout.write(f"[dry-run] remove from artists {genre.name}: artists={relations}")
                    removed_relations += relations
                    removed_genres += 1 if relations else 0
                    continue

                removed_relations += relations
                genre.artists.clear()
                if _delete_if_unused(genre):
                    removed_genres += 1

            for artist_name, override in ARTIST_OVERRIDES.items():
                artists = Artist.objects.filter(name=artist_name).prefetch_related("genres")
                set_names = override.get("set")
                remove_names = override.get("remove", [])
                add_names = override.get("add", [])

                for artist in artists:
                    if set_names:
                        target_genres = [_genre_for_name(name) for name in set_names]
                        if dry_run:
                            self.stdout.write(
                                f"[dry-run] set {artist.name}: {', '.join(name for name in set_names)}"
                            )
                            override_changes += 1
                        else:
                            artist.genres.set(target_genres)
                            override_changes += 1
                        continue

                    for name in remove_names:
                        genre = Genre.objects.filter(slug=slugify(name)).first()
                        if genre is None:
                            continue
                        if dry_run:
                            if artist.genres.filter(id=genre.id).exists():
                                self.stdout.write(f"[dry-run] remove {artist.name} -> {genre.name}")
                                override_changes += 1
                            continue
                        if artist.genres.filter(id=genre.id).exists():
                            artist.genres.remove(genre)
                            override_changes += 1
                            _delete_if_unused(genre)

                    for name in add_names:
                        genre = _genre_for_name(name)
                        if dry_run:
                            if not artist.genres.filter(id=genre.id).exists():
                                self.stdout.write(f"[dry-run] add {artist.name} -> {genre.name}")
                                override_changes += 1
                            continue
                        if not artist.genres.filter(id=genre.id).exists():
                            artist.genres.add(genre)
                            override_changes += 1

            if dry_run:
                transaction.set_rollback(True)

        remaining_bad = Genre.objects.filter(slug__in=BAD_EXACT_SLUGS).count()
        self.stdout.write(
            self.style.SUCCESS(
                "Genre cleanup "
                f"{'dry-run' if dry_run else 'updated'}: "
                f"merged_relations={merged_relations} merged_genres={merged_genres} "
                f"removed_artist_relations={removed_relations} removed_genres={removed_genres} "
                f"override_changes={override_changes} "
                f"remaining_bad_genres={remaining_bad}"
            )
        )
        self.stdout.write(
            f"Totals: artists={Artist.objects.count()} albums={Album.objects.count()} songs={Song.objects.count()} genres={Genre.objects.count()}"
        )
