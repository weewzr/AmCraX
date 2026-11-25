//! Quasi-Monte Carlo designs: Sobol' sequences and Latin hypercube sampling, as in
//! `scipy.stats.qmc`.
//!
//! # Sobol'
//!
//! [`Sobol`] is a port of `scipy.stats.qmc.Sobol` with `bits = 30`: Joe-Kuo direction numbers
//! (`new-joe-kuo-6.21201`, the table SciPy ships, first [`Sobol::MAX_DIM`] dimensions exported to
//! `sobol_directions.rs`), the Bratley-Fox recurrence of `_initialize_v` and the Gray-code
//! recurrence of `_draw`. Unscrambled points equal SciPy's `scramble=False` points bit for bit.
//!
//! Scrambling is SciPy's linear matrix scramble plus digital shift (`_scramble`, `_cscramble`):
//! the shift bits and the lower-triangular matrices are drawn, in SciPy's order, as
//! `Generator.integers(0, 2, dtype=uint32)` from a [`Pcg64`]. With the same generator state the
//! points equal SciPy's bit for bit (verified for SciPy 1.18 / NumPy 2.5). This agreement depends
//! on NumPy's bounded-integer stream, which NumPy does not promise to keep across versions, so
//! across versions the scrambled design is promised only to be statistically equivalent (a
//! randomised (t, m, s)-net with the same balance properties).
//!
//! # Latin hypercube
//!
//! [`latin_hypercube`] is `scipy.stats.qmc.LatinHypercube(d, scramble).random(n)` (strength 1,
//! no optimisation): `(perm - u) / n` with `u` from `Generator.uniform` and one shuffled
//! permutation per dimension. Bit-identical to SciPy for the recorded NumPy version; across
//! versions only the stratification (exactly one point per stratum and dimension) is promised.

use crate::random::Pcg64;
use crate::sobol_directions::{MAX_DIM, POLY, VINIT, VINIT_START};
use std::fmt;

/// Number of bits of the Sobol' integers (SciPy's default `bits = 30`).
pub const SOBOL_BITS: usize = 30;

/// Invalid QMC request.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum QmcError {
    /// Dimension above the exported direction-number table.
    InvalidDimension { d: usize, max: usize },
    /// More than `2^30` points requested in total.
    TooManyPoints { requested: u64, max: u64 },
}

impl fmt::Display for QmcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            QmcError::InvalidDimension { d, max } => {
                write!(
                    f,
                    "maximum supported dimensionality is {max} (requested {d})"
                )
            }
            QmcError::TooManyPoints { requested, max } => {
                write!(
                    f,
                    "at most {max} distinct points can be generated ({requested} requested)"
                )
            }
        }
    }
}

impl std::error::Error for QmcError {}

/// Sobol' sequence generator (port of `scipy.stats.qmc.Sobol`, `bits = 30`).
#[derive(Debug, Clone, PartialEq)]
pub struct Sobol {
    d: usize,
    sv: Vec<[u32; SOBOL_BITS]>,
    quasi: Vec<u32>,
    num_generated: u64,
    scale: f64,
}

/// `_initialize_v`: direction numbers scaled to `SOBOL_BITS` bits.
fn initialize_v(d: usize) -> Vec<[u32; SOBOL_BITS]> {
    let mut v = vec![[0u32; SOBOL_BITS]; d];
    if d == 0 {
        return v;
    }
    v[0] = [1; SOBOL_BITS];
    for dd in 1..d {
        let p = POLY[dd];
        let m = (32 - p.leading_zeros() - 1) as usize;
        let start = VINIT_START[dd] as usize;
        let init = &VINIT[start..start + m];
        v[dd][..m].copy_from_slice(init);
        for j in m..SOBOL_BITS {
            let mut newv = v[dd][j - m];
            let mut pow2: u32 = 1;
            for k in 0..m {
                pow2 <<= 1;
                if (p >> (m - 1 - k)) & 1 == 1 {
                    newv ^= pow2.wrapping_mul(v[dd][j - k - 1]);
                }
            }
            v[dd][j] = newv;
        }
    }
    let mut pow2: u32 = 1;
    for col in 0..SOBOL_BITS {
        for row in v.iter_mut() {
            row[SOBOL_BITS - 1 - col] = row[SOBOL_BITS - 1 - col].wrapping_mul(pow2);
        }
        pow2 <<= 1;
    }
    v
}

impl Sobol {
    /// Dimensions available (rows of the exported Joe-Kuo table).
    pub const MAX_DIM: usize = MAX_DIM;

    fn check_dim(d: usize) -> Result<(), QmcError> {
        if d > MAX_DIM {
            return Err(QmcError::InvalidDimension { d, max: MAX_DIM });
        }
        Ok(())
    }

    /// Unscrambled sequence (`Sobol(d, scramble=False)`); the first point is the origin.
    pub fn new(d: usize) -> Result<Self, QmcError> {
        Self::check_dim(d)?;
        Ok(Sobol {
            d,
            sv: initialize_v(d),
            quasi: vec![0; d],
            num_generated: 0,
            scale: 1.0 / (1u64 << SOBOL_BITS) as f64,
        })
    }

    /// Scrambled sequence (LMS + digital shift) drawing its random bits from `rng`, in the order
    /// of SciPy's `_scramble`: first `d * 30` shift bits, then `d * 30 * 30` matrix entries.
    pub fn new_scrambled(d: usize, rng: &mut Pcg64) -> Result<Self, QmcError> {
        let mut s = Self::new(d)?;
        let mut shift = vec![0u32; d];
        for sh in shift.iter_mut() {
            for k in 0..SOBOL_BITS {
                *sh += rng.integers_u32(0, 2) << k;
            }
        }
        // ltm[dd][row][col], C order; np.tril keeps col <= row; the diagonal is then set to 1
        let mut ltm = vec![[[0u32; SOBOL_BITS]; SOBOL_BITS]; d];
        for mat in ltm.iter_mut() {
            for row in mat.iter_mut() {
                for v in row.iter_mut() {
                    *v = rng.integers_u32(0, 2);
                }
            }
        }
        for mat in ltm.iter_mut() {
            for (r, row) in mat.iter_mut().enumerate() {
                for (c, v) in row.iter_mut().enumerate() {
                    if c > r {
                        *v = 0;
                    }
                }
                row[r] = 1;
            }
        }
        // _cscramble
        for (dd, mat) in ltm.iter().enumerate() {
            for j in 0..SOBOL_BITS {
                let vdj = s.sv[dd][j];
                let mut l: u32 = 1;
                let mut t2: u32 = 0;
                for p in (0..SOBOL_BITS).rev() {
                    // cdot_pow2: row[0] is the most significant bit
                    let mut lsmdp: u32 = 0;
                    for i in 0..SOBOL_BITS {
                        lsmdp += mat[p][SOBOL_BITS - 1 - i] << i;
                    }
                    let t1 = (lsmdp & vdj).count_ones() % 2;
                    t2 += t1 * l;
                    l = l.wrapping_mul(2);
                }
                s.sv[dd][j] = t2;
            }
        }
        s.quasi = shift;
        Ok(s)
    }

    /// `scipy.stats.qmc.Sobol(d, scramble=True, rng=seed)` for an integer seed (SciPy draws from
    /// `SeedSequence(seed).spawn(1)[0]`, see [`Pcg64::scipy_qmc`]).
    pub fn scipy_scrambled(d: usize, seed: u128) -> Result<Self, QmcError> {
        let mut rng = Pcg64::scipy_qmc(seed);
        Self::new_scrambled(d, &mut rng)
    }

    /// Dimension.
    pub fn dim(&self) -> usize {
        self.d
    }

    /// Points generated so far.
    pub fn num_generated(&self) -> u64 {
        self.num_generated
    }

    fn point(&self) -> Vec<f64> {
        self.quasi
            .iter()
            .map(|&q| f64::from(q) * self.scale)
            .collect()
    }

    /// `_draw`: `n` points continuing the Gray-code recurrence from counter `num_gen`.
    fn draw(&mut self, n: usize, num_gen: u64, out: &mut Vec<Vec<f64>>) {
        for g in num_gen..num_gen + n as u64 {
            let l = g.trailing_ones() as usize; // low_0_bit(g) - 1
            for j in 0..self.d {
                self.quasi[j] ^= self.sv[j][l];
            }
            out.push(self.point());
        }
    }

    /// The next `n` points (`Sobol.random(n)`), each a vector of length `d` in [0, 1).
    pub fn random(&mut self, n: usize) -> Result<Vec<Vec<f64>>, QmcError> {
        let max = 1u64 << SOBOL_BITS;
        let total = self.num_generated + n as u64;
        if total > max {
            return Err(QmcError::TooManyPoints {
                requested: total,
                max,
            });
        }
        let mut out = Vec::with_capacity(n);
        if n == 0 {
            return Ok(out);
        }
        if self.num_generated == 0 {
            out.push(self.point());
            if n > 1 {
                self.draw(n - 1, 0, &mut out);
            }
        } else {
            let start = self.num_generated - 1;
            self.draw(n, start, &mut out);
        }
        self.num_generated = total;
        Ok(out)
    }

    /// `Sobol.random_base2(m)`: the next `2^m` points.
    pub fn random_base2(&mut self, m: u32) -> Result<Vec<Vec<f64>>, QmcError> {
        self.random(1usize << m)
    }
}

/// Latin hypercube sample (`scipy.stats.qmc.LatinHypercube(d, scramble).random(n)`, strength 1,
/// no optimisation) drawing from `rng`: `n` points of dimension `d`. With `scramble = false`
/// every point is at the centre of its stratum.
pub fn latin_hypercube(n: usize, d: usize, scramble: bool, rng: &mut Pcg64) -> Vec<Vec<f64>> {
    let samples: Vec<Vec<f64>> = if scramble {
        (0..n)
            .map(|_| (0..d).map(|_| rng.uniform(0.0, 1.0)).collect())
            .collect()
    } else {
        vec![vec![0.5; d]; n]
    };
    let mut perms: Vec<Vec<i64>> = Vec::with_capacity(d);
    for _ in 0..d {
        let mut p: Vec<i64> = (1..=n as i64).collect();
        rng.shuffle(&mut p);
        perms.push(p);
    }
    let nf = n as f64;
    (0..n)
        .map(|r| {
            (0..d)
                .map(|c| (perms[c][r] as f64 - samples[r][c]) / nf)
                .collect()
        })
        .collect()
}

/// `scipy.stats.qmc.LatinHypercube(d, scramble, rng=seed).random(n)` for an integer seed.
pub fn scipy_latin_hypercube(n: usize, d: usize, scramble: bool, seed: u128) -> Vec<Vec<f64>> {
    let mut rng = Pcg64::scipy_qmc(seed);
    latin_hypercube(n, d, scramble, &mut rng)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn stratified(points: &[Vec<f64>], dim: usize, bins: usize) -> bool {
        let mut seen = vec![false; bins];
        for p in points {
            let k = (p[dim] * bins as f64).floor() as usize;
            if k >= bins || seen[k] {
                return false;
            }
            seen[k] = true;
        }
        seen.iter().all(|s| *s)
    }

    #[test]
    fn unscrambled_first_points() {
        let mut s = Sobol::new(2).unwrap();
        let p = s.random(4).unwrap();
        assert_eq!(p[0], vec![0.0, 0.0]);
        assert_eq!(p[1], vec![0.5, 0.5]);
        assert_eq!(p[2], vec![0.75, 0.25]);
        assert_eq!(p[3], vec![0.25, 0.75]);
    }

    #[test]
    fn every_power_of_two_prefix_is_balanced() {
        for scrambled in [false, true] {
            let mut s = if scrambled {
                Sobol::scipy_scrambled(12, 2026).unwrap()
            } else {
                Sobol::new(12).unwrap()
            };
            let p = s.random_base2(8).unwrap();
            for m in 1..=8 {
                let n = 1usize << m;
                for dim in 0..12 {
                    assert!(
                        stratified(&p[..n], dim, n),
                        "m={m} dim={dim} scrambled={scrambled}"
                    );
                }
            }
        }
    }

    #[test]
    fn scrambled_mean_is_close_to_half() {
        let mut s = Sobol::scipy_scrambled(5, 11).unwrap();
        let p = s.random_base2(12).unwrap();
        for dim in 0..5 {
            let m: f64 = p.iter().map(|x| x[dim]).sum::<f64>() / p.len() as f64;
            assert!((m - 0.5).abs() < 1e-3, "dim {dim}: {m}");
        }
    }

    #[test]
    fn dimension_limit() {
        assert!(Sobol::new(Sobol::MAX_DIM).is_ok());
        assert_eq!(
            Sobol::new(Sobol::MAX_DIM + 1),
            Err(QmcError::InvalidDimension {
                d: Sobol::MAX_DIM + 1,
                max: Sobol::MAX_DIM
            })
        );
    }

    #[test]
    fn lhs_is_stratified() {
        let mut rng = Pcg64::from_seed(3);
        let p = latin_hypercube(200, 4, true, &mut rng);
        for dim in 0..4 {
            assert!(stratified(&p, dim, 200));
        }
        let c = scipy_latin_hypercube(10, 2, false, 1);
        for x in c.iter().flatten() {
            let k = x * 10.0 - 0.5;
            assert!((k - k.round()).abs() < 1e-12);
        }
    }
}
