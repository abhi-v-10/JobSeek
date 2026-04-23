import React, { useState, useRef, useEffect } from 'react';
import { countries } from '../../utils/countries';
import { ChevronDown, Search } from 'lucide-react';

interface CountryCodeSelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

const CountryCodeSelect: React.FC<CountryCodeSelectProps> = ({ value, onChange, error }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedCountry = countries.find((c) => c.dialCode === value) || countries[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredCountries = countries.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.dialCode.includes(search) ||
      c.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative flex flex-col gap-1.5" ref={dropdownRef}>
      <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Code</label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between w-full px-3 py-2 bg-white dark:bg-zinc-900 border ${
          error ? 'border-red-500' : 'border-zinc-300 dark:border-zinc-700'
        } rounded-lg text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100 transition-all`}
      >
        <span className="truncate">{selectedCountry.code} ({selectedCountry.dialCode})</span>
        <ChevronDown size={16} className="text-zinc-500" />
      </button>

      {isOpen && (
        <div className="absolute top-[100%] left-0 z-50 w-[240px] mt-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-lg overflow-hidden flex flex-col">
          <div className="p-2 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-2">
            <Search size={14} className="text-zinc-400" />
            <input
              type="text"
              className="w-full bg-transparent text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none"
              placeholder="Search country or code..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <ul className="max-h-48 overflow-y-auto p-1">
            {filteredCountries.length > 0 ? (
              filteredCountries.map((country) => (
                <li
                  key={country.code}
                  className={`px-3 py-2 text-sm cursor-pointer rounded-md flex justify-between items-center ${
                    value === country.dialCode
                      ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium'
                      : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                  }`}
                  onClick={() => {
                    onChange(country.dialCode);
                    setIsOpen(false);
                    setSearch('');
                  }}
                >
                  <span className="truncate mr-2">{country.name}</span>
                  <span className="text-zinc-500 dark:text-zinc-400 shrink-0">{country.dialCode}</span>
                </li>
              ))
            ) : (
              <li className="px-3 py-4 text-sm text-zinc-500 text-center">No countries found</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CountryCodeSelect;
