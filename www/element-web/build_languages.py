from tree_sitter import Language

Language.build_library(
  # Çıkış dosyası (oluşacak .so dosyası)
  'build/my-languages.so',
  [
    'tree-sitter-javascript'  # hangi grammar’ı build edeceğiz
  ]
)
