pub fn crate_ok() -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crate_ok() {
        assert!(crate_ok());
    }
}
