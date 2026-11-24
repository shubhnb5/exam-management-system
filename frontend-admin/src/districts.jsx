// The 36 districts of Maharashtra (current official English names). The
// value is what gets saved and printed on admit cards; `hint` shows the
// former name in the dropdown. Keep in sync with
// backend/app/validators.py MAHARASHTRA_DISTRICTS.
export const DISTRICTS = [
  { value: "Ahilyanagar", hint: "Ahmednagar" },
  { value: "Akola" },
  { value: "Amravati" },
  { value: "Beed" },
  { value: "Bhandara" },
  { value: "Buldhana" },
  { value: "Chandrapur" },
  { value: "Chhatrapati Sambhajinagar", hint: "Aurangabad" },
  { value: "Dharashiv", hint: "Osmanabad" },
  { value: "Dhule" },
  { value: "Gadchiroli" },
  { value: "Gondia" },
  { value: "Hingoli" },
  { value: "Jalgaon" },
  { value: "Jalna" },
  { value: "Kolhapur" },
  { value: "Latur" },
  { value: "Mumbai City" },
  { value: "Mumbai Suburban" },
  { value: "Nagpur" },
  { value: "Nanded" },
  { value: "Nandurbar" },
  { value: "Nashik" },
  { value: "Palghar" },
  { value: "Parbhani" },
  { value: "Pune" },
  { value: "Raigad" },
  { value: "Ratnagiri" },
  { value: "Sangli" },
  { value: "Satara" },
  { value: "Sindhudurg" },
  { value: "Solapur" },
  { value: "Thane" },
  { value: "Wardha" },
  { value: "Washim" },
  { value: "Yavatmal" },
];

export function DistrictOptions() {
  return (
    <>
      <option value="">Select district</option>
      {DISTRICTS.map((d) => (
        <option key={d.value} value={d.value}>
          {d.hint ? `${d.value} (${d.hint})` : d.value}
        </option>
      ))}
    </>
  );
}
