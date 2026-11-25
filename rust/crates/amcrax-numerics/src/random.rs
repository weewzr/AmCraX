//! NumPy-compatible random numbers: `SeedSequence` and the `PCG64` bit generator.
//!
//! * [`SeedSequence`] is a port of `numpy.random.SeedSequence` (pool size 4): entropy
//!   assembly, `hashmix`/`mix`, `generate_state` and `spawn`.
//! * [`Pcg64`] is `numpy.random.PCG64`: the 128-bit LCG with multiplier
//!   `0x2360ED051FC65DA44385DF649FCCF645`, XSL-RR output (state advanced before the output is
//!   taken), seeded from four `u64` words of `SeedSequence::generate_state`.
//!
//! Bit-identical to NumPy (checked against NumPy 2.5 in `tests/golden.rs`): the raw 64-bit
//! output, the buffered 32-bit output, `Generator.random()` (`(next_u64 >> 11) * 2^-53`),
//! `Generator.uniform(low, high)`, `Generator.integers(low, high, dtype=uint32)` for the
//! ranges used here, and `Generator.shuffle` (`random_interval`).
//!
//! Not promised bit-identical: normal and other non-uniform variates (NumPy uses a ziggurat
//! that is not ported), and shuffles or bounded integers across NumPy versions (NumPy does not
//! guarantee these streams to stay fixed). Monte Carlo results that use them are compared
//! statistically.

const INIT_A: u32 = 0x43b0_d7e5;
const MULT_A: u32 = 0x931e_8875;
const INIT_B: u32 = 0x8b51_f9dd;
const MULT_B: u32 = 0x58f3_8ded;
const MIX_MULT_L: u32 = 0xca01_f9dd;
const MIX_MULT_R: u32 = 0x4973_f715;
const XSHIFT: u32 = 16;
const POOL_SIZE: usize = 4;

/// PCG default 128-bit multiplier (`PCG_DEFAULT_MULTIPLIER_128`).
const PCG_MULT: u128 = 0x2360_ED05_1FC6_5DA4_4385_DF64_9FCC_F645;

/// Little-endian 32-bit words of a non-negative integer (`_int_to_uint32_array`); `[0]` for 0.
pub fn int_to_u32_words(mut n: u128) -> Vec<u32> {
    if n == 0 {
        return vec![0];
    }
    let mut out = Vec::new();
    while n > 0 {
        out.push((n & 0xFFFF_FFFF) as u32);
        n >>= 32;
    }
    out
}

/// Port of `numpy.random.SeedSequence` with the default pool size 4.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeedSequence {
    entropy: Vec<u32>,
    spawn_key: Vec<u64>,
    pool: [u32; POOL_SIZE],
    n_children_spawned: u64,
}

#[inline]
fn hashmix(value: u32, hash_const: &mut u32) -> u32 {
    let mut v = value ^ *hash_const;
    *hash_const = hash_const.wrapping_mul(MULT_A);
    v = v.wrapping_mul(*hash_const);
    v ^= v >> XSHIFT;
    v
}

#[inline]
fn mix(x: u32, y: u32) -> u32 {
    let mut r = MIX_MULT_L
        .wrapping_mul(x)
        .wrapping_sub(MIX_MULT_R.wrapping_mul(y));
    r ^= r >> XSHIFT;
    r
}

impl SeedSequence {
    /// `SeedSequence(entropy)` for an integer seed below 2^128.
    pub fn new(entropy: u128) -> Self {
        Self::from_words(&int_to_u32_words(entropy), &[])
    }

    /// `SeedSequence(entropy, spawn_key=spawn_key)` with the entropy given as little-endian
    /// 32-bit words (as `_coerce_to_uint32_array` produces them, `[0]` for zero).
    pub fn from_words(entropy: &[u32], spawn_key: &[u64]) -> Self {
        let mut ss = SeedSequence {
            entropy: entropy.to_vec(),
            spawn_key: spawn_key.to_vec(),
            pool: [0; POOL_SIZE],
            n_children_spawned: 0,
        };
        let assembled = ss.assembled_entropy();
        ss.mix_entropy(&assembled);
        ss
    }

    fn assembled_entropy(&self) -> Vec<u32> {
        let mut run = self.entropy.clone();
        let mut spawn = Vec::new();
        for &k in &self.spawn_key {
            spawn.extend(int_to_u32_words(u128::from(k)));
        }
        if !spawn.is_empty() && run.len() < POOL_SIZE {
            run.resize(POOL_SIZE, 0);
        }
        run.extend(spawn);
        run
    }

    fn mix_entropy(&mut self, entropy: &[u32]) {
        let mut hash_const = INIT_A;
        let mixer = &mut self.pool;
        for i in 0..POOL_SIZE {
            let v = if i < entropy.len() { entropy[i] } else { 0 };
            mixer[i] = hashmix(v, &mut hash_const);
        }
        for i_src in 0..POOL_SIZE {
            for i_dst in 0..POOL_SIZE {
                if i_src != i_dst {
                    let h = hashmix(mixer[i_src], &mut hash_const);
                    mixer[i_dst] = mix(mixer[i_dst], h);
                }
            }
        }
        for &e in entropy.iter().skip(POOL_SIZE) {
            for i_dst in 0..POOL_SIZE {
                let h = hashmix(e, &mut hash_const);
                mixer[i_dst] = mix(mixer[i_dst], h);
            }
        }
    }

    /// The mixed entropy pool (`SeedSequence.pool`).
    pub fn pool(&self) -> [u32; POOL_SIZE] {
        self.pool
    }

    /// The spawn key (`SeedSequence.spawn_key`).
    pub fn spawn_key(&self) -> &[u64] {
        &self.spawn_key
    }

    /// `generate_state(n_words, dtype=np.uint32)`.
    pub fn generate_state_u32(&self, n_words: usize) -> Vec<u32> {
        let mut hash_const = INIT_B;
        let mut out = Vec::with_capacity(n_words);
        for i in 0..n_words {
            let mut v = self.pool[i % POOL_SIZE];
            v ^= hash_const;
            hash_const = hash_const.wrapping_mul(MULT_B);
            v = v.wrapping_mul(hash_const);
            v ^= v >> XSHIFT;
            out.push(v);
        }
        out
    }

    /// `generate_state(n_words, dtype=np.uint64)` (pairs of 32-bit words, little-endian).
    pub fn generate_state_u64(&self, n_words: usize) -> Vec<u64> {
        let w = self.generate_state_u32(2 * n_words);
        (0..n_words)
            .map(|i| u64::from(w[2 * i]) | (u64::from(w[2 * i + 1]) << 32))
            .collect()
    }

    /// The number of children spawned so far (`SeedSequence.n_children_spawned`).
    pub fn n_children_spawned(&self) -> u64 {
        self.n_children_spawned
    }

    /// Set the spawn counter (to resume a sequence whose earlier children were spawned elsewhere).
    pub fn set_children_spawned(&mut self, n: u64) {
        self.n_children_spawned = n;
    }

    /// `spawn(n_children)`: children with spawn keys `spawn_key + (i,)` continuing the count.
    pub fn spawn(&mut self, n_children: usize) -> Vec<SeedSequence> {
        let start = self.n_children_spawned;
        let out = (start..start + n_children as u64)
            .map(|i| {
                let mut key = self.spawn_key.clone();
                key.push(i);
                SeedSequence::from_words(&self.entropy, &key)
            })
            .collect();
        self.n_children_spawned += n_children as u64;
        out
    }
}

/// The C-library calls of NumPy's ziggurat: `exp(-x^2/2)` of a wedge test (with the layer and
/// the left-hand side it is compared with) and `log1p(-u)` of a tail attempt. NumPy calls the
/// platform C library (`exp`, `npy_log1p`); [`NativeMath`] calls the Rust standard library, which
/// calls the C library of the target.
pub trait ZigMath {
    fn exp(&mut self, arg: f64, layer: usize, lhs: f64) -> f64;
    fn log1p(&mut self, arg: f64) -> f64;
    /// Index of the draw about to be generated (for tracing).
    fn set_draw(&mut self, _i: usize) {}
}

/// The native C-library functions.
pub struct NativeMath;

impl ZigMath for NativeMath {
    #[inline]
    fn exp(&mut self, arg: f64, _layer: usize, _lhs: f64) -> f64 {
        arg.exp()
    }
    #[inline]
    fn log1p(&mut self, arg: f64) -> f64 {
        arg.ln_1p()
    }
}

/// Port of NumPy's `PCG64` bit generator together with the `Generator` methods used by AmCraX.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pcg64 {
    state: u128,
    inc: u128,
    has_uint32: bool,
    uinteger: u32,
}

impl Pcg64 {
    /// `PCG64(seed_sequence)`.
    pub fn from_seed_sequence(ss: &SeedSequence) -> Self {
        let v = ss.generate_state_u64(4);
        let initstate = (u128::from(v[0]) << 64) | u128::from(v[1]);
        let initseq = (u128::from(v[2]) << 64) | u128::from(v[3]);
        let mut rng = Pcg64 {
            state: 0,
            inc: (initseq << 1) | 1,
            has_uint32: false,
            uinteger: 0,
        };
        rng.step();
        rng.state = rng.state.wrapping_add(initstate);
        rng.step();
        rng
    }

    /// `numpy.random.default_rng(seed)` for an integer seed below 2^128.
    pub fn from_seed(seed: u128) -> Self {
        Self::from_seed_sequence(&SeedSequence::new(seed))
    }

    /// The generator SciPy's QMC engines (`Sobol`, `LatinHypercube`) create from an integer
    /// `rng=seed`: they spawn one child, `SeedSequence(seed).spawn(1)[0]`.
    pub fn scipy_qmc(seed: u128) -> Self {
        let mut root = SeedSequence::new(seed);
        let child = root.spawn(1).remove(0);
        Self::from_seed_sequence(&child)
    }

    #[inline]
    fn step(&mut self) {
        self.state = self.state.wrapping_mul(PCG_MULT).wrapping_add(self.inc);
    }

    /// Next raw 64-bit output (`PCG64.random_raw()`).
    #[inline]
    pub fn next_u64(&mut self) -> u64 {
        self.step();
        let s = self.state;
        let x = ((s >> 64) as u64) ^ (s as u64);
        let rot = (s >> 122) as u32;
        x.rotate_right(rot)
    }

    /// Next 32-bit output with NumPy's buffering: the low half of a 64-bit draw first, then the
    /// high half.
    #[inline]
    pub fn next_u32(&mut self) -> u32 {
        if self.has_uint32 {
            self.has_uint32 = false;
            return self.uinteger;
        }
        let n = self.next_u64();
        self.has_uint32 = true;
        self.uinteger = (n >> 32) as u32;
        (n & 0xFFFF_FFFF) as u32
    }

    /// `Generator.random()`: uniform double in [0, 1) with 53 random bits.
    #[inline]
    pub fn random(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / 9_007_199_254_740_992.0)
    }

    /// `Generator.standard_normal()`: NumPy's 256-layer ziggurat (`random_standard_normal`,
    /// tables in `ziggurat_tables.rs`).
    pub fn standard_normal(&mut self) -> f64 {
        self.standard_normal_with(&mut NativeMath)
    }

    /// [`Pcg64::standard_normal`] with the two C-library calls of the ziggurat (`exp` of a wedge
    /// test, `log1p` of a tail attempt) supplied by `m` (for the platform experiment of stage 5).
    pub fn standard_normal_with<M: ZigMath>(&mut self, m: &mut M) -> f64 {
        use crate::ziggurat_tables::{FI, KI, WI};
        const R: f64 = 3.654_152_885_361_009;
        const INV_R: f64 = 0.273_661_237_329_758_3;
        loop {
            let mut r = self.next_u64();
            let idx = (r & 0xff) as usize;
            r >>= 8;
            let sign = r & 0x1;
            let rabs = (r >> 1) & 0x000f_ffff_ffff_ffff;
            let mut x = rabs as f64 * WI[idx];
            if sign & 0x1 == 1 {
                x = -x;
            }
            if rabs < KI[idx] {
                return x;
            }
            if idx == 0 {
                loop {
                    let l1 = m.log1p(-self.random());
                    let l2 = m.log1p(-self.random());
                    let xx = -INV_R * l1;
                    let yy = -l2;
                    if yy + yy > xx * xx {
                        return if (rabs >> 8) & 0x1 == 1 {
                            -(R + xx)
                        } else {
                            R + xx
                        };
                    }
                }
            } else {
                let lhs = (FI[idx - 1] - FI[idx]) * self.random() + FI[idx];
                if lhs < m.exp(-0.5 * x * x, idx, lhs) {
                    return x;
                }
            }
        }
    }

    /// `n` values of [`Pcg64::standard_normal_with`]; `m.set_draw(i)` before draw `i`.
    pub fn standard_normal_vec_with<M: ZigMath>(&mut self, n: usize, m: &mut M) -> Vec<f64> {
        let mut out = Vec::with_capacity(n);
        for i in 0..n {
            m.set_draw(i);
            out.push(self.standard_normal_with(m));
        }
        out
    }

    /// `Generator.normal(loc, scale)` = `loc + scale * standard_normal()`.
    pub fn normal(&mut self, loc: f64, scale: f64) -> f64 {
        loc + scale * self.standard_normal()
    }

    /// `n` values of [`Pcg64::random`].
    pub fn random_vec(&mut self, n: usize) -> Vec<f64> {
        (0..n).map(|_| self.random()).collect()
    }

    /// `Generator.uniform(low, high)` = `low + (high - low) * random()`.
    #[inline]
    pub fn uniform(&mut self, low: f64, high: f64) -> f64 {
        let range = high - low;
        low + range * self.random()
    }

    /// `Generator.triangular(left, mode, right)` (NumPy `random_triangular`: inverse CDF of one
    /// `random()` draw).
    pub fn triangular(&mut self, left: f64, mode: f64, right: f64) -> f64 {
        let base = right - left;
        let leftbase = mode - left;
        let ratio = leftbase / base;
        let leftprod = leftbase * base;
        let rightprod = (right - mode) * base;
        let u = self.random();
        if u <= ratio {
            left + (u * leftprod).sqrt()
        } else {
            right - ((1.0 - u) * rightprod).sqrt()
        }
    }

    /// `Generator.integers(0, n, size)` for the default `int64` dtype and `1 <= n <= 2^32`:
    /// NumPy routes ranges that fit 32 bits to the buffered 32-bit Lemire generator (one call of
    /// [`Pcg64::integers_u32`] per value).
    pub fn integers_below(&mut self, n: u64) -> u64 {
        if n == 1 {
            return 0;
        }
        if n - 1 == u64::from(u32::MAX) {
            return u64::from(self.next_u32());
        }
        u64::from(self.integers_u32(0, n as u32))
    }

    /// `Generator.integers(low, high, dtype=np.uint32)` (exclusive `high`): Lemire's method on
    /// 32-bit draws, as NumPy's `buffered_bounded_lemire_uint32`.
    pub fn integers_u32(&mut self, low: u32, high: u32) -> u32 {
        assert!(high > low, "high must be greater than low");
        let rng = high - low - 1;
        if rng == 0 {
            return low;
        }
        if rng == u32::MAX {
            return low.wrapping_add(self.next_u32());
        }
        let rng_excl = rng + 1;
        let mut m = u64::from(self.next_u32()) * u64::from(rng_excl);
        let mut leftover = (m & 0xFFFF_FFFF) as u32;
        if leftover < rng_excl {
            let threshold = (u32::MAX - rng) % rng_excl;
            while leftover < threshold {
                m = u64::from(self.next_u32()) * u64::from(rng_excl);
                leftover = (m & 0xFFFF_FFFF) as u32;
            }
        }
        low + (m >> 32) as u32
    }

    /// NumPy's `random_interval(max)`: uniform integer in `[0, max]` by masked rejection.
    pub fn random_interval(&mut self, max: u64) -> u64 {
        if max == 0 {
            return 0;
        }
        let mut mask = max;
        mask |= mask >> 1;
        mask |= mask >> 2;
        mask |= mask >> 4;
        mask |= mask >> 8;
        mask |= mask >> 16;
        mask |= mask >> 32;
        if max <= 0xFFFF_FFFF {
            loop {
                let v = u64::from(self.next_u32()) & mask;
                if v <= max {
                    return v;
                }
            }
        }
        loop {
            let v = self.next_u64() & mask;
            if v <= max {
                return v;
            }
        }
    }

    /// `Generator.shuffle` of a 1-D array (Fisher-Yates from the end with
    /// [`Pcg64::random_interval`]).
    pub fn shuffle<T>(&mut self, a: &mut [T]) {
        let n = a.len();
        for i in (1..n).rev() {
            let j = self.random_interval(i as u64) as usize;
            a.swap(i, j);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn words_of_integers() {
        assert_eq!(int_to_u32_words(0), vec![0]);
        assert_eq!(int_to_u32_words(1 << 32), vec![0, 1]);
        assert_eq!(int_to_u32_words(u128::MAX), vec![u32::MAX; 4]);
    }

    #[test]
    fn random_is_in_unit_interval() {
        let mut g = Pcg64::from_seed(20261123);
        for _ in 0..10_000 {
            let u = g.random();
            assert!((0.0..1.0).contains(&u));
        }
    }

    #[test]
    fn u32_buffering_uses_both_halves() {
        let mut a = Pcg64::from_seed(5);
        let mut b = a.clone();
        let full = b.next_u64();
        assert_eq!(a.next_u32(), (full & 0xFFFF_FFFF) as u32);
        assert_eq!(a.next_u32(), (full >> 32) as u32);
    }

    #[test]
    fn spawn_continues_counting() {
        let mut root = SeedSequence::new(7);
        let a = root.spawn(2);
        let b = root.spawn(1);
        assert_eq!(a[0].spawn_key(), &[0]);
        assert_eq!(a[1].spawn_key(), &[1]);
        assert_eq!(b[0].spawn_key(), &[2]);
        assert_ne!(a[0].pool(), a[1].pool());
    }

    #[test]
    fn integers_and_interval_stay_in_range() {
        let mut g = Pcg64::from_seed(1);
        for _ in 0..1000 {
            assert!(g.integers_u32(3, 10) < 10);
            assert!(g.random_interval(6) <= 6);
            assert!(g.random_interval(1 << 40) <= 1 << 40);
        }
        let mut v: Vec<u32> = (0..50).collect();
        g.shuffle(&mut v);
        let mut s = v.clone();
        s.sort_unstable();
        assert_eq!(s, (0..50).collect::<Vec<u32>>());
    }
}
