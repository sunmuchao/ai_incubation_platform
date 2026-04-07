import { useState, useEffect } from 'react'

export function useToggle(initialValue = false): [boolean, () => void] {
  const [value, setValue] = useState(initialValue)
  const toggle = () => setValue((v) => !v)
  return [value, toggle]
}

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      return initialValue
    }
  })

  const setValue = (value: T) => {
    try {
      setStoredValue(value)
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error('Error saving to localStorage:', error)
    }
  }

  return [storedValue, setValue]
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export function usePagination(initialPage = 1, initialPageSize = 10) {
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)

  const nextPage = () => setPage((p) => p + 1)
  const prevPage = () => setPage((p) => Math.max(1, p - 1))
  const goToPage = (p: number) => setPage(p)
  const reset = () => {
    setPage(initialPage)
    setPageSize(initialPageSize)
  }

  return {
    page,
    pageSize,
    nextPage,
    prevPage,
    goToPage,
    reset,
    setPageSize,
  }
}

export function useForm<T extends Record<string, any>>(initialValues: T) {
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({})
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({})

  const handleChange = (field: keyof T, value: any) => {
    setValues((v) => ({ ...v, [field]: value }))
    if (errors[field]) {
      setErrors((e) => ({ ...e, [field]: undefined }))
    }
  }

  const handleBlur = (field: keyof T) => {
    setTouched((t) => ({ ...t, [field]: true }))
  }

  const validate = (validator: (values: T) => Partial<Record<keyof T, string>>) => {
    const newErrors = validator(values)
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const reset = () => {
    setValues(initialValues)
    setErrors({})
    setTouched({})
  }

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validate,
    reset,
    setValues,
  }
}
