/**
 * Sample lessons for the in-memory API used by tests and the demo build.
 * Dates are given as days before "today" so the demo always looks current.
 */
import type {
  Direction,
  FurtherItem,
  GlossaryEntry,
  Illustration,
  Job,
  SubjectId,
} from '../lib/api';

export interface SampleLesson {
  id: string;
  daysAgo: number;
  subject: SubjectId;
  origin: Job['kind'];
  title: string;
  hook: string;
  readingMinutes: number;
  tags: string[];
  body: string;
  keyIdeas: string[];
  glossary: GlossaryEntry[];
  goDeeper: Direction[];
  further: FurtherItem[];
  illustrations: Illustration[];
  parentId?: string;
  requestText?: string;
  opened?: boolean;
  finished?: boolean;
  saved?: boolean;
  rating?: -1 | 0 | 1;
  scroll?: number;
}

const commons = 'https://upload.wikimedia.org/wikipedia/commons/thumb';
// The Wikipedia API now also returns thumbnails on this host.
const thumbs = 'https://thumb.wikimedia.org/wikipedia/commons/thumb';

const MILKMAID: Illustration = {
  image_url: `${commons}/6/6e/Johannes_Vermeer_-_Het_melkmeisje_-_Google_Art_Project.png/960px-Johannes_Vermeer_-_Het_melkmeisje_-_Google_Art_Project.png`,
  page_url: 'https://en.wikipedia.org/wiki/The_Milkmaid_(Vermeer)',
  title: 'The Milkmaid (Vermeer)',
  caption:
    'The Milkmaid, about 1658. Oil on canvas, 45.5 × 41 cm. Rijksmuseum, Amsterdam.',
  width: 960,
  height: 1079,
};

const DELFT: Illustration = {
  image_url: `${thumbs}/a/a2/Vermeer-view-of-delft.jpg/960px-Vermeer-view-of-delft.jpg`,
  page_url: 'https://en.wikipedia.org/wiki/View_of_Delft',
  title: 'View of Delft',
  caption:
    'View of Delft, about 1660–61. The yellow roof Proust admired is right of centre.',
  width: 960,
  height: 797,
};

const ORESME: Illustration = {
  image_url: `${commons}/3/35/Oresme.jpg/960px-Oresme.jpg`,
  page_url: 'https://en.wikipedia.org/wiki/Nicole_Oresme',
  title: 'Nicole Oresme',
  caption:
    'Nicole Oresme in a fifteenth-century manuscript of his translation of Aristotle.',
  width: 960,
  height: 949,
};

const ROSETTA: Illustration = {
  image_url: `${thumbs}/2/23/Rosetta_Stone.JPG/960px-Rosetta_Stone.JPG`,
  page_url: 'https://en.wikipedia.org/wiki/Rosetta_Stone',
  title: 'Rosetta Stone',
  caption:
    'The Rosetta Stone in the British Museum: hieroglyphs at the top, Demotic in the middle, Greek below.',
  width: 960,
  height: 1124,
};

const HASH_DIAGRAM: Illustration = {
  image_url: `${commons}/7/7d/Hash_table_3_1_1_0_1_0_0_SP.svg/960px-Hash_table_3_1_1_0_1_0_0_SP.svg.png`,
  page_url: 'https://en.wikipedia.org/wiki/Hash_table',
  title: 'Hash table',
  caption:
    'A small phone book stored as a hash table: each name is hashed to a bucket.',
  width: 960,
  height: 701,
};

const VERMEER_BODY = `Stand in front of *The Milkmaid* in the Rijksmuseum and the first surprise is its size: the canvas is about the height of a sheet of newspaper. The second is how quiet it is. A woman pours milk from a jug into a bowl. Nothing else happens, and nothing else needs to.

## A room built out of light

Vermeer gives the scene one source of light, a window on the left, and then lets every surface answer it differently. The whitewashed wall is not white at all: it moves from a warm grey near the window to a cooler, almost greenish tone behind the woman's back. That shift is what makes the wall read as a wall, with air in front of it, rather than a flat backdrop.

Look at where the light lands and how it is described:

- **The bread and the basket** are covered in small, separate dots of pale paint, a technique often called *pointillé*. Up close they look like sparks; from a step back they become the dry crust of bread catching the sun.
- **The jug and the stream of milk** are painted with almost no detail. The milk is a few strokes, yet it reads as moving.
- **The wall** keeps a nail and the small hole of another one, with a tiny shadow under each. Vermeer could have left them out.

## Blue that cost more than gold

The woman's apron and the cloth on the table are painted with natural ultramarine, a pigment ground from lapis lazuli mined in what is now Afghanistan. In Vermeer's time it was among the most expensive colours a painter could buy. He used it generously, and not only where you see bright blue: it sits under some of the shadows, cooling them.

> “Vermeer’s pictures are not about events. They are about attention.”
> — a common way of summing him up, and a fair warning not to look for a story

That is an interpretation, not a documented intention. Vermeer left no letters about his work, and only about 35 paintings are firmly attributed to him.

## Did he use a camera obscura?

A camera obscura is a darkened box or room in which a lens projects an image of the scene onto a surface. Some historians, notably Philip Steadman, argue that Vermeer used one: the soft highlights in his paintings look like the out-of-focus points of light a simple lens produces, and the proportions of some rooms fit the idea. Others point out that no document mentions such a device in his studio and that a skilled painter can learn to see those effects without one. The question is still open, and it does not change what is on the canvas.

## The same light outdoors

A few years later Vermeer painted *View of Delft*, his town seen across the water under a broken sky. Marcel Proust admired one detail so much that, in his novel *In Search of Lost Time*, the writer Bergotte dies in front of it, regretting that his own books were not built from patient layers like “that little patch of yellow wall.”

## How to look at it

Give the painting a slow minute. Start at the window, follow the light down the woman's arm to the jug, then across the table to the bread. Notice how each material, from linen to brass to crust, is described with a different kind of mark. That is most of the lesson: Vermeer's subject is how ordinary things look when you finally pay attention to them.`;

const HARMONIC_BODY = `Take a step of one metre, then half a metre, then a third, then a quarter, and keep going. Each step is shorter than the last, and after a thousand steps you are moving less than a millimetre at a time. Surely the walk has a finish line?

It does not. Given enough steps you can walk past any point you name. This lesson is about why.

## The series

The sum of the steps is the **harmonic series**:

$$
1 + \\frac{1}{2} + \\frac{1}{3} + \\frac{1}{4} + \\frac{1}{5} + \\cdots
$$

We write $H_n$ for the sum of the first $n$ terms. The terms shrink towards zero, which is necessary for a sum to settle on a finite value, but it is not enough.

## Oresme’s argument

Around 1350 the French scholar Nicole Oresme gave a proof that still works perfectly. Group the terms so that each group ends at a power of two:

$$
1 + \\frac{1}{2} + \\left(\\frac{1}{3} + \\frac{1}{4}\\right) + \\left(\\frac{1}{5} + \\cdots + \\frac{1}{8}\\right) + \\left(\\frac{1}{9} + \\cdots + \\frac{1}{16}\\right) + \\cdots
$$

Now replace every term in a group by the smallest one in that group. Each term only gets smaller, so the total can only go down:

1. $\\frac{1}{3} + \\frac{1}{4}$ is at least $\\frac{1}{4} + \\frac{1}{4} = \\frac{1}{2}$.
2. The four terms from $\\frac{1}{5}$ to $\\frac{1}{8}$ are at least $4 \\times \\frac{1}{8} = \\frac{1}{2}$.
3. The eight terms from $\\frac{1}{9}$ to $\\frac{1}{16}$ are at least $8 \\times \\frac{1}{16} = \\frac{1}{2}$.

Every group adds at least one half, and there are infinitely many groups. So $H_{2^k} \\ge 1 + \\frac{k}{2}$, which grows without limit.

## How slowly it grows

The sum diverges, but at a crawl. It grows like the natural logarithm:

$$
H_n \\approx \\ln n + \\gamma, \\qquad \\gamma \\approx 0.5772
$$

| $n$ | $H_n$ | $\\ln n + \\gamma$ |
| ---: | ---: | ---: |
| 10 | 2.9290 | 2.8798 |
| 100 | 5.1874 | 5.1824 |
| 1,000 | 7.4855 | 7.4850 |
| 1,000,000 | 14.3927 | 14.3927 |

A million terms get you past 14. To pass 100 you would need more terms than there are atoms in the observable universe.

## A worked example: stacking books

Put a book at the edge of a table and slide it out until it is about to fall: it can overhang by half its length. Now stack books on top of each other, each shifted out as far as it can go. With careful placement, $n$ books can overhang by

$$
\\frac{1}{2} H_n \\text{ book lengths.}
$$

With four books, $\\frac{1}{2}\\left(1 + \\frac{1}{2} + \\frac{1}{3} + \\frac{1}{4}\\right) \\approx 1.04$: the top book sits entirely beyond the table's edge. Because $H_n$ has no limit, a tall enough stack can reach as far out as you like, though very slowly.

## Where the line is

Square the denominators and the story changes completely:

$$
1 + \\frac{1}{4} + \\frac{1}{9} + \\frac{1}{16} + \\cdots = \\frac{\\pi^2}{6}
$$

Euler found that value in 1734. The terms $\\frac{1}{n^2}$ shrink fast enough; the terms $\\frac{1}{n}$ do not. Telling the two kinds of sums apart is the starting point of the study of convergence.`;

const HASH_BODY = `Ask a list for a name and it has to look at every entry until it finds a match. Ask a hash table and it goes almost straight to the right place, whether it holds ten names or ten million. The trick is to turn the key into an address.

## From key to bucket

A hash table keeps an array of *buckets*. To store a key, it runs the key through a **hash function** that produces a number, then takes that number modulo the array's length to get a bucket index. To look the key up later, it does the same calculation and checks just that bucket.

\`\`\`python
class HashTable:
    def __init__(self, size=8):
        self.buckets = [[] for _ in range(size)]

    def _bucket(self, key):
        return self.buckets[hash(key) % len(self.buckets)]

    def put(self, key, value):
        bucket = self._bucket(key)
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))

    def get(self, key):
        for k, v in self._bucket(key):
            if k == key:
                return v
        raise KeyError(key)
\`\`\`

## Collisions

Two different keys can land in the same bucket; with more keys than buckets it is guaranteed. The code above handles this with **chaining**: each bucket holds a short list. As long as the lists stay short, lookups stay fast.

What keeps them short is the **load factor**, the number of stored keys divided by the number of buckets, written $\\alpha$. When $\\alpha$ passes a threshold, the table allocates a larger array (often twice the size) and moves every key to its new bucket. That resize is slow, but it happens rarely enough that the average cost per insertion stays constant.

## Open addressing

The other main approach stores keys directly in the array and, on a collision, *probes* for the next free slot. With linear probing, Knuth's analysis gives the expected number of slots examined:

| Load factor $\\alpha$ | Found | Not found |
| :--- | ---: | ---: |
| 0.50 | 1.5 | 2.5 |
| 0.75 | 2.5 | 8.5 |
| 0.90 | 5.5 | 50.5 |

The numbers stay small until the table is nearly full, then climb steeply. This is why real implementations resize well before they are full.

## Where you meet them

Python's \`dict\`, JavaScript's \`Map\`, database indexes, caches, and compilers' symbol tables are all built on hashing. The idea is old, from the early 1950s at IBM, and it remains one of the most useful in computing.`;

const ROSETTA_BODY = `In July 1799 French soldiers rebuilding a fort near the town of Rashid, which Europeans called Rosetta, in the Nile Delta, found a broken slab of dark stone covered in writing. The officer in charge, Pierre-François Bouchard, saw that it carried three kinds of script and understood it might matter.

## One decree, three scripts

The stone is a copy of a decree issued at Memphis in 196 BC by a council of priests honouring the young king Ptolemy V. The same text appears three times: in **hieroglyphs**, the formal script of temples; in **Demotic**, the everyday Egyptian script of the period; and in **ancient Greek**, the language of the ruling Ptolemaic court. The Greek ends with the instruction that gave the stone its value:

> This decree shall be inscribed on a stela of hard stone in sacred and native and Greek characters.

Scholars could read Greek. If the three texts said the same thing, the Greek was a key.

## A British prize

After the French surrender in Egypt, the Treaty of Alexandria in 1801 handed the stone to the British. It has been in the British Museum since 1802, and Egypt has asked for its return.

## The race

Copies circulated across Europe. Two scholars made the decisive progress:

- **Thomas Young**, an English physician and physicist, showed around 1814–19 that the oval rings called cartouches held royal names, and matched the signs in one of them to the name Ptolemy.
- **Jean-François Champollion**, a French linguist who knew Coptic, the late form of the Egyptian language, went further. In his *Lettre à M. Dacier* of September 1822 he showed that hieroglyphs combined sound signs and meaning signs, and soon read names and words well beyond royal titles.

A family story says Champollion ran into his brother's office shouting “Je tiens l’affaire!” (“I've got it!”) and fainted. It comes from his nephew's account and may be polished, but the decipherment itself is well documented.

## What it changed

Within a generation scholars could read temple walls, tombs, and papyri directly. Three thousand years of Egyptian writing became history in the Egyptians' own words rather than in the accounts of Greek visitors.`;

const DUSK_BODY = `The end of the day has a surprising number of words, from the technical to the poetic. Here are five worth keeping, each with a slightly different shade of meaning.

## crepuscular

*kri-PUS-kyuh-ler*, adjective. Relating to twilight; in biology, active at dawn and dusk.

From Latin *crepusculum*, “twilight.” Its everyday use is literary; its scientific use is precise.

- Deer and rabbits are crepuscular, which is why you see them at the edges of the day.
- The photograph had a crepuscular blue that made the street look older than it was.

## gloaming

*GLOH-ming*, noun. The fading light of evening.

From Old English *glōmung*, related to “glow.” It survived in Scots and northern English and is now mostly poetic.

- They walked home through the gloaming, past windows just being lit.

## vespertine

*VES-per-tyne*, adjective. Of, or happening in, the evening; in botany, flowering in the evening.

From Latin *vesper*, “evening,” the same root as *vespers*, the evening prayer.

- Evening primroses are vespertine, opening as the light goes.

## tenebrous

*TEN-uh-brus*, adjective. Dark, shadowy; sometimes obscure in meaning.

From Latin *tenebrae*, “darkness.” Painters use the related *tenebrism* for strong contrasts of light and shadow, as in Caravaggio.

- The tenebrous hallway smelled of old paper.

## eventide

*EE-vun-tide*, noun. Evening.

From Old English *ǣfentīd*. Archaic, kept alive by hymns such as “Abide with Me.” Use it knowingly.`;

const OPEN_ADDRESSING_BODY = `Chaining keeps a little list in every bucket. Open addressing keeps everything in the array itself, which is faster on modern hardware because neighbouring slots share a cache line. The price is a subtle problem with deletion.

## Probing

To insert a key, compute its home slot. If the slot is taken, try the next one, and the next, until you find a free one. A lookup follows the same path and stops at the first empty slot: if the key were in the table, it would have been placed before that gap.

## The tombstone problem

That stopping rule breaks if you delete a key by simply emptying its slot. A later key that was pushed past it would become unreachable. The usual fix is a **tombstone**: a marker meaning “something was here, keep looking.” Tombstones keep lookups correct, but they pile up and slow every search until the table is rebuilt.

## Robin Hood hashing

A clever variant moves keys around on insert so that no key ends up much further from its home than any other. The name comes from taking slots from keys that are close to home (rich) and giving them to keys that are far away (poor). It keeps probe lengths short and predictable even at high load factors.`;

function shortBody(paragraphs: string[]): string {
  return paragraphs.join('\n\n');
}

const SHARED_DIRECTIONS: Direction[] = [
  {
    title: 'The people behind it',
    description:
      'Who did the work, what they were trying to do, and what it cost them.',
  },
  {
    title: 'What came next',
    description:
      'How the idea was taken up, argued over, and changed by later generations.',
  },
  {
    title: 'A closer look at one detail',
    description: 'Slow down on a single example and examine it properly.',
  },
];

export const SAMPLE_LESSONS: SampleLesson[] = [
  {
    id: 'l-vermeer',
    daysAgo: 0,
    subject: 'art',
    origin: 'daily',
    title: 'What Vermeer’s Milkmaid does with a single window',
    hook: 'A woman pours milk, and nothing else happens. Why has this small, quiet painting held people for more than three and a half centuries?',
    readingMinutes: 11,
    tags: ['Vermeer', 'Dutch Golden Age', 'light', 'pigment'],
    body: VERMEER_BODY,
    keyIdeas: [
      'The Milkmaid is built from one light source, and every surface answers it differently.',
      'Small dots of pale paint (pointillé) turn bread and basket into points of light.',
      'Natural ultramarine, more costly than gold, gives the blues and cools the shadows.',
      'Whether Vermeer used a camera obscura is still debated; the evidence is suggestive, not documentary.',
    ],
    glossary: [
      {
        term: 'Camera obscura',
        definition:
          'A darkened box or room in which a lens or small hole projects an image of the scene outside onto a surface.',
      },
      {
        term: 'Pointillé',
        definition:
          'Small separate dots of light paint used to suggest glinting highlights.',
      },
      {
        term: 'Ultramarine',
        definition:
          'A deep blue pigment ground from lapis lazuli; very expensive before a synthetic version appeared in the 1820s.',
      },
      {
        term: 'Genre painting',
        definition:
          'A painting of everyday life and ordinary people rather than history, religion, or myth.',
      },
    ],
    goDeeper: [
      {
        title: 'Vermeer’s blues',
        description:
          'How ultramarine was made, what it cost, and where Vermeer hid it in his paintings.',
      },
      {
        title: 'The camera obscura debate',
        description:
          'The evidence for and against Vermeer using a lens, and why it is so hard to settle.',
      },
      {
        title: 'View of Delft up close',
        description:
          'His only true cityscape, and the patch of yellow wall that Proust wrote about.',
      },
    ],
    further: [
      { title: 'The Milkmaid', creator: 'Johannes Vermeer', kind: 'artwork' },
      {
        title: 'Vermeer’s Camera',
        creator: 'Philip Steadman',
        kind: 'book',
        note: 'The case for the camera obscura, argued carefully.',
      },
      {
        title: 'Tim’s Vermeer',
        creator: 'Teller',
        kind: 'film',
        note: 'An inventor tries to repaint a Vermeer with optics.',
      },
      { title: 'Rijksmuseum', kind: 'place' },
    ],
    illustrations: [MILKMAID, DELFT],
  },
  {
    id: 'l-hash',
    daysAgo: 2,
    subject: 'computing',
    origin: 'surprise',
    title: 'How a hash table finds anything in one step',
    hook: 'A list has to look at every entry. A hash table goes almost straight to the answer, whether it holds ten names or ten million.',
    readingMinutes: 12,
    tags: ['data structures', 'hashing', 'algorithms'],
    body: HASH_BODY,
    keyIdeas: [
      'A hash function turns a key into a bucket index, so a lookup checks one place instead of all of them.',
      'Collisions are unavoidable; chaining and open addressing are the two main ways to handle them.',
      'The load factor decides speed: tables resize before they get too full.',
    ],
    glossary: [
      {
        term: 'Hash function',
        definition:
          'A function that maps a key to a number, the same number every time for the same key.',
      },
      {
        term: 'Load factor',
        definition:
          'The number of stored keys divided by the number of buckets.',
      },
      {
        term: 'Chaining',
        definition:
          'Handling collisions by keeping a small list in each bucket.',
      },
    ],
    goDeeper: [
      {
        title: 'Open addressing and tombstones',
        description:
          'Storing keys in the array itself, and why deletion is tricky.',
      },
      {
        title: 'What makes a good hash function',
        description:
          'Spreading keys evenly, and how attackers exploit weak ones.',
      },
      {
        title: 'Hashing in databases',
        description:
          'Hash indexes, hash joins, and when a tree is the better choice.',
      },
    ],
    further: [
      {
        title: 'The Art of Computer Programming, Volume 3',
        creator: 'Donald Knuth',
        kind: 'book',
      },
    ],
    illustrations: [HASH_DIAGRAM],
    opened: true,
    scroll: 0.45,
  },
  {
    id: 'l-hash-2',
    daysAgo: 1,
    subject: 'computing',
    origin: 'follow_up',
    parentId: 'l-hash',
    title: 'When two keys want the same seat: open addressing',
    hook: 'Keeping every key in one flat array is fast, until you try to delete something.',
    readingMinutes: 6,
    tags: ['hashing', 'data structures'],
    body: OPEN_ADDRESSING_BODY,
    keyIdeas: [
      'Open addressing stores keys in the array and probes for a free slot on collision.',
      'Deleting by emptying a slot breaks lookups; tombstones fix that at a cost.',
      'Robin Hood hashing keeps probe lengths even by moving keys on insert.',
    ],
    glossary: [
      {
        term: 'Tombstone',
        definition:
          'A marker left in a deleted slot so that lookups keep searching past it.',
      },
    ],
    goDeeper: SHARED_DIRECTIONS,
    further: [],
    illustrations: [],
    opened: true,
    scroll: 0.2,
  },
  {
    id: 'l-harmonic',
    daysAgo: 3,
    subject: 'math',
    origin: 'subject',
    title: 'Why adding ever-smaller steps can still take you anywhere',
    hook: 'One metre, then a half, then a third, then a quarter. The steps shrink forever, and yet the walk never ends.',
    readingMinutes: 13,
    tags: ['series', 'infinity', 'Oresme', 'logarithms'],
    body: HARMONIC_BODY,
    keyIdeas: [
      'The harmonic series 1 + 1/2 + 1/3 + … grows without limit even though its terms shrink to zero.',
      'Oresme’s proof groups terms into blocks that each add at least one half.',
      'The growth is logarithmic: a million terms only reach about 14.4.',
      'Squaring the denominators makes the sum converge, to π²/6.',
    ],
    glossary: [
      {
        term: 'Series',
        definition:
          'The sum of the terms of a sequence, possibly infinitely many.',
      },
      {
        term: 'Diverge',
        definition:
          'Of a series: to have partial sums that do not settle on a finite value.',
      },
      {
        term: 'Euler–Mascheroni constant',
        definition: 'The number γ ≈ 0.5772, the limit of Hₙ − ln n as n grows.',
      },
    ],
    goDeeper: [
      {
        title: 'The Basel problem',
        description: 'How Euler found that the sum of 1/n² is exactly π²/6.',
      },
      {
        title: 'Tests for convergence',
        description:
          'The comparison, ratio, and integral tests, with examples.',
      },
      {
        title: 'The book-stacking puzzle',
        description:
          'How far a stack of books can lean, and better stacks than the obvious one.',
      },
    ],
    further: [
      {
        title: 'Gamma: Exploring Euler’s Constant',
        creator: 'Julian Havil',
        kind: 'book',
      },
      { title: 'Nicole Oresme', kind: 'article' },
    ],
    illustrations: [ORESME],
    opened: true,
    finished: true,
    saved: true,
    rating: 1,
    scroll: 1,
  },
  {
    id: 'l-rosetta',
    daysAgo: 5,
    subject: 'history',
    origin: 'daily',
    title: 'The Rosetta Stone and the race to read hieroglyphs',
    hook: 'A broken slab found in a fort wall carried the same decree three times. It took twenty-three years to make the third script speak.',
    readingMinutes: 10,
    tags: ['Egypt', 'decipherment', 'Champollion'],
    body: ROSETTA_BODY,
    keyIdeas: [
      'The stone repeats one decree of 196 BC in hieroglyphs, Demotic, and Greek.',
      'Thomas Young linked cartouches to royal names; Champollion showed how the script worked.',
      'Decipherment let historians read Egypt in its own words.',
    ],
    glossary: [
      {
        term: 'Cartouche',
        definition: 'An oval ring around a royal name in hieroglyphic writing.',
      },
      {
        term: 'Demotic',
        definition:
          'A cursive Egyptian script used for everyday documents from about 650 BC.',
      },
      {
        term: 'Coptic',
        definition:
          'The last stage of the Egyptian language, written in a Greek-based alphabet.',
      },
    ],
    goDeeper: SHARED_DIRECTIONS,
    further: [
      {
        title: 'The Writing of the Gods',
        creator: 'Edward Dolnick',
        kind: 'book',
      },
      { title: 'British Museum', kind: 'place' },
    ],
    illustrations: [ROSETTA],
    opened: true,
    finished: true,
    scroll: 1,
  },
  {
    id: 'l-dusk',
    daysAgo: 8,
    subject: 'words',
    origin: 'topic',
    requestText: 'words for dusk',
    title: 'Five words for the end of the day',
    hook: 'From the scientist’s crepuscular to the poet’s gloaming: a small vocabulary for the hour when the light goes.',
    readingMinutes: 6,
    tags: ['vocabulary', 'Latin roots', 'evening'],
    body: DUSK_BODY,
    keyIdeas: [
      'Crepuscular is literary in everyday use and exact in biology.',
      'Gloaming survived through Scots and is now mostly poetic.',
      'Vespertine and vespers share the Latin vesper, evening.',
    ],
    glossary: [
      {
        term: 'crepuscular',
        definition: 'Relating to twilight; active at dawn and dusk.',
      },
      { term: 'gloaming', definition: 'The fading light of evening.' },
      {
        term: 'vespertine',
        definition: 'Of the evening; flowering in the evening.',
      },
      {
        term: 'tenebrous',
        definition: 'Dark, shadowy; sometimes obscure in meaning.',
      },
      { term: 'eventide', definition: 'Evening (archaic).' },
    ],
    goDeeper: SHARED_DIRECTIONS,
    further: [],
    illustrations: [],
    opened: true,
    finished: true,
    saved: true,
    scroll: 1,
  },
  {
    id: 'l-sky',
    daysAgo: 11,
    subject: 'science',
    origin: 'surprise',
    title: 'Why the sky is blue and sunsets are red',
    hook: 'The same tiny collisions between sunlight and air explain both, and they also explain why distant hills look blue.',
    readingMinutes: 9,
    tags: ['light', 'atmosphere', 'Rayleigh scattering'],
    body: shortBody([
      'Sunlight contains every visible colour. As it passes through the air, molecules of nitrogen and oxygen scatter some of it in all directions, and they scatter short wavelengths far more than long ones: blue light about five times as strongly as red. Look at any part of the sky away from the sun and you see that scattered light, which is mostly blue.',
      '## Sunsets',
      'At sunset the light reaching you has crossed much more air. Most of the blue has been scattered out of the beam along the way, so what is left is orange and red. Dust and smoke add their own scattering and can make sunsets redder still.',
      '## How we know',
      'Lord Rayleigh worked out the mathematics in 1871: scattering by particles much smaller than the wavelength goes as the inverse fourth power of the wavelength, $I \\propto 1/\\lambda^4$. Measurements of skylight and laboratory experiments with gases agree with it closely.',
    ]),
    keyIdeas: [
      'Air molecules scatter blue light more than red.',
      'At sunset the long path through air removes the blue.',
      'Rayleigh scattering goes as 1/λ⁴.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [],
    illustrations: [],
    opened: true,
    finished: true,
    scroll: 1,
  },
  {
    id: 'l-ozu',
    daysAgo: 24,
    subject: 'film',
    origin: 'daily',
    title: 'How Tokyo Story films a family from knee height',
    hook: 'Ozu’s camera sits low, rarely moves, and lets rooms stay empty after people leave. The style is the meaning.',
    readingMinutes: 12,
    tags: ['Ozu', 'Japanese cinema', '1950s'],
    body: shortBody([
      'Yasujirō Ozu’s *Tokyo Story* (1953) follows an elderly couple who travel to Tokyo to visit their grown children, who are too busy for them. The plot is simple; the way it is filmed is not.',
      '## The low camera',
      'Ozu usually places the camera low, roughly at the eye level of someone kneeling on a tatami mat, and he almost never moves it. Conversations are filmed with characters facing nearly straight into the lens. The effect is calm and slightly formal, as if we were another guest in the room.',
      '## Pillow shots',
      'Between scenes Ozu cuts to quiet views: chimneys, washing on a line, an empty corridor. Critics call them “pillow shots”. They give the film room to breathe and let feelings settle without dialogue.',
    ]),
    keyIdeas: [
      'A low, still camera makes the viewer a quiet guest.',
      'Pillow shots give time for feeling between scenes.',
      'Restraint carries the emotion.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [{ title: 'Tokyo Story', creator: 'Yasujirō Ozu', kind: 'film' }],
    illustrations: [],
    opened: true,
    finished: true,
    saved: true,
    rating: 1,
    scroll: 1,
  },
  {
    id: 'l-hormuz',
    daysAgo: 29,
    subject: 'geography',
    origin: 'subject',
    title: 'Why one narrow strait matters to the whole world',
    hook: 'At its narrowest the Strait of Hormuz is about 33 kilometres wide, and a large share of the world’s seaborne oil passes through it.',
    readingMinutes: 11,
    tags: ['Persian Gulf', 'energy', 'chokepoints'],
    body: shortBody([
      'The Strait of Hormuz connects the Persian Gulf to the Gulf of Oman and the open ocean. Iran lies to the north; the Musandam peninsula of Oman to the south. The shipping lanes themselves are only a few kilometres wide.',
      '## A chokepoint',
      'Tankers leaving Saudi Arabia, Iraq, Kuwait, Qatar, the United Arab Emirates, and Iran must pass through it. Pipelines can bypass part of the flow, but not most of it. That is why tensions in the strait move oil prices far from the Gulf. Figures change from year to year, so treat any single number with care.',
    ]),
    keyIdeas: [
      'Hormuz is the only sea route out of the Persian Gulf.',
      'Bypass pipelines cover only part of the flow.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [],
    illustrations: [],
    opened: true,
    rating: -1,
    scroll: 0.3,
  },
  {
    id: 'l-theseus',
    daysAgo: 38,
    subject: 'philosophy',
    origin: 'surprise',
    title: 'The ship of Theseus, plank by plank',
    hook: 'Replace every plank of a ship one at a time. Is it still the same ship, and if you rebuild the old planks, which one is?',
    readingMinutes: 10,
    tags: ['identity', 'metaphysics', 'Plutarch'],
    body: shortBody([
      'Plutarch records that the Athenians kept the ship in which Theseus returned from Crete, replacing its rotting timbers with new ones, and that philosophers argued over whether it remained the same ship.',
      '## Hobbes’s twist',
      'Thomas Hobbes added a second ship: suppose someone collects the discarded planks and reassembles them. Now two ships have a claim to be the original. The puzzle forces a choice between continuity of form and continuity of material.',
    ]),
    keyIdeas: [
      'Identity over time can follow form or matter.',
      'Hobbes’s version makes the two answers compete.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [],
    illustrations: [],
    opened: true,
    finished: true,
    scroll: 1,
  },
  {
    id: 'l-fugue',
    daysAgo: 45,
    subject: 'music',
    origin: 'daily',
    title: 'What makes a fugue a fugue',
    hook: 'One short tune enters alone, then again and again in other voices, until a whole structure has grown from it.',
    readingMinutes: 11,
    tags: ['Bach', 'counterpoint', 'Baroque'],
    body: shortBody([
      'A fugue begins with a single voice playing the subject, a short melody of a few bars. A second voice then enters with the same melody in a different key, usually a fifth higher, while the first continues with a countersubject.',
      '## What to listen for',
      'Try Bach’s Fugue in C minor from Book I of *The Well-Tempered Clavier*. Count the entries of the subject in the first minute, and notice how each new voice changes the texture without losing the thread.',
    ]),
    keyIdeas: [
      'A fugue grows from one subject entering in turn.',
      'The exposition presents every voice.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [
      {
        title: 'The Well-Tempered Clavier',
        creator: 'Johann Sebastian Bach',
        kind: 'music',
      },
    ],
    illustrations: [],
  },
  {
    id: 'l-middlemarch',
    daysAgo: 52,
    subject: 'literature',
    origin: 'topic',
    requestText: 'the ending of Middlemarch',
    title: 'Reading the last paragraph of Middlemarch',
    hook: 'George Eliot ends a vast novel by praising lives that leave no monument. The sentence rewards slow reading.',
    readingMinutes: 9,
    tags: ['George Eliot', 'Victorian novel'],
    body: shortBody([
      '*Middlemarch* (1871–72) ends with a reflection on Dorothea, whose life did not become the great reforming career she once imagined. Eliot turns that apparent failure into her final argument.',
      '> for the growing good of the world is partly dependent on unhistoric acts',
      'Read the closing sentence aloud and notice the rhythm: long, qualified clauses that settle on “unvisited tombs.” The grammar does what the meaning says, giving weight to what is quiet.',
    ]),
    keyIdeas: [
      'The ending values unrecorded goodness.',
      'Its rhythm enacts its meaning.',
    ],
    glossary: [],
    goDeeper: SHARED_DIRECTIONS,
    further: [{ title: 'Middlemarch', creator: 'George Eliot', kind: 'book' }],
    illustrations: [],
    opened: true,
    finished: true,
    saved: true,
    scroll: 1,
  },
];

/** Templates for lessons the fake worker "prepares" on request. */
export const PREPARED_TEMPLATES: Partial<Record<SubjectId, string>> = {
  art: 'l-vermeer',
  math: 'l-harmonic',
  computing: 'l-hash',
  history: 'l-rosetta',
  words: 'l-dusk',
};
