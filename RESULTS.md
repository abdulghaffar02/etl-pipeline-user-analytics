# Results

Computed from 333,034 listens loaded from `dataset.txt` (sha256 `f95f49d73a87`).

Full results for every query are in [`results/`](results/).

Regenerate with `make analyze`. How each question was interpreted is in the [README](README.md#analysis).

## a1_top_users

Top 10 users by number of songs listened to (every listen counts, including repeats).

| user_name | number_of_listens |
|---|---|
| hds | 46885 |
| Groschi | 14959 |
| Silent Singer | 13005 |
| phdnk | 12861 |
| 6d6f7274686f6e | 11544 |
| reverbel | 8398 |
| Cl�psHydra | 8318 |
| InvincibleAsia | 7804 |
| cimualte | 7356 |
| inhji | 6349 |

## a2_users_on_2019_03_01

Users who listened to at least one song on 2019-03-01 (UTC).

| number_of_users |
|---|
| 75 |

## a3_first_song_per_user

First song each user listened to.

| user_name | listened_at | track_name | artist_name | release_name |
|---|---|---|---|---|
| 6d6f7274686f6e | 2019-01-01 10:41:51 | The Leper Affinity | Opeth | Blackwater Park |
| Adsky_traktor | 2019-01-01 09:24:44 | Сердце с долгом разлучается | Константин Беляев | Что-то сигарета гаснет |
| AllSparks | 2019-01-02 08:48:19 | Fever | Balthazar | Fever |
| AlwinHummels | 2019-02-24 11:40:47 | Geef me je angst | Andre Hazes | Voor Jou |
| Arcor | 2019-01-01 01:22:23 | Exsultate Justi | John Williams | Empire of the Sun |
| AscendedGravity | 2019-01-01 23:01:17 | Amoeba | Adolescents | Adolescents |
| Bezvezenator | 2019-01-01 06:19:22 | Devour | Marilyn Manson | The High End Of Low |
| BiamBioum | 2019-01-07 13:56:07 | Beirut (14.12.16 - Live in Paris) | Ibrahim Maalouf | 14.12.16 - Live In Paris |
| BlackGauna | 2019-01-01 18:36:09 | Visionz | Wu-Tang Clan | Wu-Tang Forever |
| Boris_Neo | 2019-01-22 16:48:27 | Keep You Close | Deus | Keep You Close |
| BornabeWylde | 2019-04-14 14:01:05 | Wow. | Post Malone | Wow. |
| Bound2Fate | 2019-01-01 00:07:01 | Home Invasion | Steven Wilson | Hand. Cannot. Erase. |
| Canis_L_Sapien | 2019-01-03 08:39:29 | Wolves | Marshmello & Selena Gomez | Wolves |
| Cl�psHydra | 2019-01-01 13:09:35 | Hym | Isis | Oceanic |
| Cooked_Bread | 2019-02-14 03:07:36 | All These Things I Hate (Revolve Around Me) | Bullet for My Valentine | The Poison |
| CraxorAdam | 2019-02-25 17:33:36 | Prophecy | Terry Devine-King | Society, Religion & Humanity |
| DJ.Xcite | 2019-01-02 00:27:26 | Top 20 | Best Female Metal and Hard Rock Singers |  |
| Dazzel | 2019-01-03 10:26:56 | The Departure | Michael Nyman | The Piano Sings |
| Devvy | 2019-02-21 00:23:38 | Stop Torturing Me | Wicca Phase Springs Eternal | Stop Torturing Me |
| DivineNightmare | 2019-02-24 20:32:53 | Birdie | Avril Lavigne | Head Above Water |

First 20 of 202 rows, all of them in [`results/a3_first_song_per_user.csv`](results/a3_first_song_per_user.csv).

## b_top_days_per_user

Each user's 3 days with the most listens.

| user | number_of_listens | date |
|---|---|---|
| 6d6f7274686f6e | 204 | 2019-01-27 |
| 6d6f7274686f6e | 198 | 2019-01-14 |
| 6d6f7274686f6e | 196 | 2019-03-15 |
| Adsky_traktor | 109 | 2019-01-03 |
| Adsky_traktor | 99 | 2019-01-05 |
| Adsky_traktor | 86 | 2019-01-04 |
| AllSparks | 114 | 2019-01-31 |
| AllSparks | 81 | 2019-01-23 |
| AllSparks | 72 | 2019-01-11 |
| AlwinHummels | 1 | 2019-02-24 |
| Arcor | 133 | 2019-03-02 |
| Arcor | 111 | 2019-03-01 |
| Arcor | 86 | 2019-03-16 |
| AscendedGravity | 77 | 2019-02-26 |
| AscendedGravity | 61 | 2019-04-09 |
| AscendedGravity | 55 | 2019-04-05 |
| Bezvezenator | 92 | 2019-01-16 |
| Bezvezenator | 89 | 2019-01-20 |
| Bezvezenator | 75 | 2019-01-17 |
| BiamBioum | 34 | 2019-04-12 |

First 20 of 577 rows, all of them in [`results/b_top_days_per_user.csv`](results/b_top_days_per_user.csv).

## c_daily_active_users

Daily active users: a user is active on day X if they listened in [X-6 days, X].

| date | number_active_users | percentage_active_users |
|---|---|---|
| 2019-01-01 | 72 | 35.64 |
| 2019-01-02 | 95 | 47.03 |
| 2019-01-03 | 103 | 50.99 |
| 2019-01-04 | 107 | 52.97 |
| 2019-01-05 | 108 | 53.47 |
| 2019-01-06 | 110 | 54.46 |
| 2019-01-07 | 114 | 56.44 |
| 2019-01-08 | 113 | 55.94 |
| 2019-01-09 | 115 | 56.93 |
| 2019-01-10 | 115 | 56.93 |
| 2019-01-11 | 114 | 56.44 |
| 2019-01-12 | 112 | 55.45 |
| 2019-01-13 | 114 | 56.44 |
| 2019-01-14 | 119 | 58.91 |
| 2019-01-15 | 118 | 58.42 |
| 2019-01-16 | 120 | 59.41 |
| 2019-01-17 | 120 | 59.41 |
| 2019-01-18 | 118 | 58.42 |
| 2019-01-19 | 119 | 58.91 |
| 2019-01-20 | 118 | 58.42 |

First 20 of 105 rows, all of them in [`results/c_daily_active_users.csv`](results/c_daily_active_users.csv).
