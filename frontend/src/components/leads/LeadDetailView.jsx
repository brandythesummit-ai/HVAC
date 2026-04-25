import { formatDate, formatCurrency } from '../../utils/formatters';

/**
 * Expanded "Full detail" view rendered inside DetailSheet's bottom-half
 * disclosure. Shows the property fields the field rep cares about that
 * aren't already in DetailSheet's compact top section: address, owner
 * contact, lot size, year built, parcel number, etc.
 *
 * Data shape: the /api/leads/by-property/:id endpoint flattens property
 * fields onto the top-level lead object; /api/leads (list) returns them
 * nested under `lead.properties`. Read from whichever is present so this
 * component works regardless of which endpoint produced the lead.
 *
 * What's intentionally NOT shown here:
 *   - "Recommended Pipeline" / "Contact Completeness" / "Affluence Tier"
 *     — those columns were dropped in migration 052
 *   - Raw Accela permit data sub-sections (Addresses/Owners/Parcels)
 *     — neither endpoint joins permits.raw_data, so they were always
 *     "No data available". Re-add when the permit fetch is wired up.
 */
const LeadDetailView = ({ lead }) => {
  const property = lead.properties || lead || {};

  const Field = ({ label, value }) => (
    <>
      <div className="font-medium text-gray-600">{label}:</div>
      <div className="text-gray-900">{value || '-'}</div>
    </>
  );

  return (
    <div className="bg-gray-50 border-t border-gray-200">
      <div className="px-6 py-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Property detail</h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <Field label="Owner" value={property.owner_name} />
          <Field label="Phone" value={property.owner_phone} />
          <Field label="Email" value={property.owner_email} />
          <Field label="Address" value={property.normalized_address} />
          <Field
            label="HVAC age"
            value={property.hvac_age_years != null ? `${property.hvac_age_years} yrs` : null}
          />
          <Field label="Most recent HVAC" value={formatDate(property.most_recent_hvac_date)} />
          <Field label="Property value" value={formatCurrency(property.total_property_value)} />
          <Field
            label="Lot size"
            value={property.lot_size_sqft ? `${property.lot_size_sqft.toLocaleString()} sqft` : null}
          />
          <Field label="Year built" value={property.year_built} />
          <Field label="Parcel #" value={property.parcel_number} />
          <Field
            label="Score source"
            value={
              property.score_source === 'permit'
                ? '✓ Confirmed via permit'
                : property.score_source === 'year_built'
                ? 'ⓘ Estimated from year built'
                : null
            }
          />
        </div>
      </div>
    </div>
  );
};

export default LeadDetailView;
