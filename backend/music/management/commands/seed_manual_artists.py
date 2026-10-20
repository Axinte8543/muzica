from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from music.models import Artist, Genre


def _normalize_name(value: str) -> str:
	return " ".join(str(value or "").strip().split())


def _unique_slug_for_artist(base: str) -> str:
	base_slug = slugify(_normalize_name(base))
	if not base_slug:
		base_slug = "artist"

	slug = base_slug
	suffix = 2
	while Artist.objects.filter(slug=slug).exists():
		slug = f"{base_slug}-{suffix}"
		suffix += 1
	return slug


def _get_or_create_genre(name: str) -> Genre:
	clean = _normalize_name(name)
	if not clean:
		raise ValueError("Empty genre")

	slug = slugify(clean) or "genre"
                                                                        
	obj, _ = Genre.objects.get_or_create(name=clean, defaults={"slug": slug})
                                                                   
	return obj


@dataclass(frozen=True)
class SeedArtist:
	name: str
	genres: tuple[str, ...]
	is_romanian: bool = True


SEED_ARTISTS: list[SeedArtist] = [
                        
 SeedArtist("Norzeatic", ("Hip-Hop",)),
 SeedArtist("Deceneu", ("Hip-Hop",)),
 SeedArtist("RACLA", ("Hip-Hop",)),
 SeedArtist("Brugner", ("Hip-Hop",)),
 SeedArtist("DJ Undoo", ("Hip-Hop",)),
 SeedArtist("Butch", ("Hip-Hop",)),
 SeedArtist("Psihotrop", ("Hip-Hop",)),
 SeedArtist("Bean MC", ("Hip-Hop",)),
 SeedArtist("Jianu", ("Hip-Hop",)),
 SeedArtist("Stres", ("Hip-Hop",)),

                  
 SeedArtist("MGK666", ("Trap",)),
 SeedArtist("M.G.L.", ("Trap",)),
 SeedArtist("OG Eastbull", ("Trap",)),
 SeedArtist("Killa Flex", ("Trap",)),
 SeedArtist("Albert NBN", ("Trap",)),
 SeedArtist("Sez", ("Trap",)),
 SeedArtist("YNY Sebi", ("Trap",)),
 SeedArtist("R3hab", ("Electronic",)),
 SeedArtist("Azteca x Ian", ("Trap",)),
 SeedArtist("Ninos", ("Trap",)),

                          
 SeedArtist("Randi", ("Pop",)),
 SeedArtist("Sonny Flame", ("Pop",)),
 SeedArtist("What's UP", ("Pop",)),
 SeedArtist("DJ Yaang", ("Pop",)),
 SeedArtist("Alex Velea", ("Pop",)),
 SeedArtist("Shift", ("Pop",)),
 SeedArtist("Doddy", ("Pop",)),
 SeedArtist("Giulia", ("Pop",)),
 SeedArtist("CRBL", ("Pop",)),
 SeedArtist("Lino Golden", ("Pop",)),

                             
 SeedArtist("Semnal M", ("Rock",)),
 SeedArtist("Ro-Mania", ("Rock",)),
 SeedArtist("Metrock", ("Rock",)),
 SeedArtist("Antract", ("Rock",)),
 SeedArtist("Hara", ("Rock",)),
 SeedArtist("Kumm", ("Rock",)),
 SeedArtist("Blazzaj", ("Rock",)),
 SeedArtist("Travka", ("Rock",)),
 SeedArtist("Firma", ("Rock",)),
 SeedArtist("The Amsterdams", ("Rock",)),

                      
 SeedArtist("Ioan Gyuri Pascu", ("Folk",)),
 SeedArtist("Alexandru Andrieș", ("Folk",)),
 SeedArtist("Ștefan Hrușcă", ("Folk",)),
 SeedArtist("Mircea Rusu", ("Folk",)),
 SeedArtist("Vali Sterian", ("Folk",)),

                            
 SeedArtist("Subcarpați Orchestra", ("Electronic",)),
 SeedArtist("Golan", ("Electronic",)),
 SeedArtist("Argatu’", ("Electronic",)),
 SeedArtist("DJ Vasile", ("Electronic",)),
 SeedArtist("Electric Brother", ("Electronic",)),
]


class Command(BaseCommand):
	help = "Seed a curated list of Romanian-scene artists (manual), creating/updating Artist + Genre and marking them approved."

	def add_arguments(self, parser):
		parser.add_argument(
		 "--dry-run",
		 action="store_true",
		 help="Show what would change, without writing to DB",
		)

	def handle(self, *args, **options):
		dry_run: bool = bool(options.get("dry_run"))

		created = 0
		updated = 0
		unchanged = 0
		genre_cache: dict[str, Genre] = {}

		for seed in SEED_ARTISTS:
			name = _normalize_name(seed.name)
			if not name:
				continue

           
			genres: list[Genre] = []
			for g in seed.genres:
				gkey = _normalize_name(g).lower()
				if not gkey:
					continue
				if gkey not in genre_cache:
					genre_cache[gkey] = _get_or_create_genre(g)
				genres.append(genre_cache[gkey])

			with transaction.atomic():
				artist = Artist.objects.filter(name__iexact=name).first()
				if artist is None:
					if dry_run:
						self.stdout.write(self.style.WARNING(f"[dry-run] create artist: {name}"))
						created += 1
						continue

					artist = Artist(
					 name=name,
					 slug=_unique_slug_for_artist(name),
					 is_romanian=True,
					 is_approved=True,
					)
					if not dry_run:
						artist.save()
						if genres:
							artist.genres.add(*genres)
					created += 1
					continue

				dirty_fields: list[str] = []
                                                                                   
				if artist.is_approved is not True:
					artist.is_approved = True
					dirty_fields.append("is_approved")
				if bool(seed.is_romanian) and artist.is_romanian is not True:
					artist.is_romanian = True
					dirty_fields.append("is_romanian")

				if dirty_fields:
					if dry_run:
						self.stdout.write(
						 self.style.WARNING(f"[dry-run] update artist: {artist.name} ({', '.join(dirty_fields)})")
						)
						updated += 1
					else:
						artist.save(update_fields=list(dict.fromkeys(dirty_fields)))
						updated += 1
				else:
					unchanged += 1

				if genres and not dry_run:
                                                 
					existing_ids = set(artist.genres.values_list("id", flat=True))
					to_add = [g for g in genres if g.id not in existing_ids]
					if to_add:
						artist.genres.add(*to_add)

		self.stdout.write(
		 self.style.SUCCESS(
		  f"Done. artists: created={created}, updated={updated}, unchanged={unchanged}. genres_touched={len(genre_cache)}"
		 )
		)
