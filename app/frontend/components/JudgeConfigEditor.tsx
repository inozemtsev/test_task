import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

export interface JudgeConfig {
  entity_types: string[];
  profile_name: string;
  numeric_tolerance_percent: number;
  date_granularity: string;
  case_insensitive_strings: boolean;
  ignore_minor_wording_diffs: boolean;
  require_all_fields_match: boolean;
  required_key_fields: string[];
  allow_partial_matches: boolean;
  extra_instructions: string | null;
}

interface JudgeConfigEditorProps {
  config: JudgeConfig | null;
  onChange: (config: JudgeConfig) => void;
}

const DEFAULT_CONFIG: JudgeConfig = {
  entity_types: [],
  profile_name: 'custom',
  numeric_tolerance_percent: 0.0,
  date_granularity: 'day',
  case_insensitive_strings: false,
  ignore_minor_wording_diffs: false,
  require_all_fields_match: false,
  required_key_fields: [],
  allow_partial_matches: true,
  extra_instructions: null,
};

const AVAILABLE_ENTITY_TYPES = [
  'assets',
  'debts',
  'income',
  'pensions',
  'expenses',
  'clients',
  'properties',
  'accounts',
];

const PROFILES = [
  { value: 'strict', label: 'Strict', description: 'Exact matching, all fields required' },
  { value: 'lenient', label: 'Lenient', description: 'Flexible matching, partial matches allowed' },
  { value: 'custom', label: 'Custom', description: 'Configure your own matching rules' },
];

export function JudgeConfigEditor({ config, onChange }: JudgeConfigEditorProps) {
  const [localConfig, setLocalConfig] = useState<JudgeConfig>(config || DEFAULT_CONFIG);
  const [newKeyField, setNewKeyField] = useState('');

  useEffect(() => {
    if (config) {
      setLocalConfig(config);
    }
  }, [config]);

  const updateConfig = (updates: Partial<JudgeConfig>) => {
    const newConfig = { ...localConfig, ...updates };
    setLocalConfig(newConfig);
    onChange(newConfig);
  };

  const toggleEntityType = (type: string) => {
    const newTypes = localConfig.entity_types.includes(type)
      ? localConfig.entity_types.filter((t) => t !== type)
      : [...localConfig.entity_types, type];
    updateConfig({ entity_types: newTypes });
  };

  const addKeyField = () => {
    if (newKeyField.trim() && !localConfig.required_key_fields.includes(newKeyField.trim())) {
      updateConfig({
        required_key_fields: [...localConfig.required_key_fields, newKeyField.trim()],
      });
      setNewKeyField('');
    }
  };

  const removeKeyField = (field: string) => {
    updateConfig({
      required_key_fields: localConfig.required_key_fields.filter((f) => f !== field),
    });
  };

  const applyProfile = (profileName: string) => {
    let updates: Partial<JudgeConfig> = { profile_name: profileName };

    if (profileName === 'strict') {
      updates = {
        ...updates,
        numeric_tolerance_percent: 0,
        case_insensitive_strings: false,
        ignore_minor_wording_diffs: false,
        require_all_fields_match: true,
        allow_partial_matches: false,
      };
    } else if (profileName === 'lenient') {
      updates = {
        ...updates,
        numeric_tolerance_percent: 5,
        case_insensitive_strings: true,
        ignore_minor_wording_diffs: true,
        require_all_fields_match: false,
        allow_partial_matches: true,
      };
    }

    updateConfig(updates);
  };

  return (
    <div className="space-y-6">
      {/* Profile Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Judge Profile</CardTitle>
          <CardDescription>Choose a preset or configure custom matching rules</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Profile</Label>
            <Select value={localConfig.profile_name} onValueChange={applyProfile}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROFILES.map((profile) => (
                  <SelectItem key={profile.value} value={profile.value}>
                    <div>
                      <div className="font-medium">{profile.label}</div>
                      <div className="text-xs text-muted-foreground">{profile.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Entity Types */}
      <Card>
        <CardHeader>
          <CardTitle>Entity Types in Scope</CardTitle>
          <CardDescription>Select which fact types this judge should evaluate</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {AVAILABLE_ENTITY_TYPES.map((type) => (
              <div key={type} className="flex items-center space-x-2">
                <Checkbox
                  id={`entity-${type}`}
                  checked={localConfig.entity_types.includes(type)}
                  onCheckedChange={() => toggleEntityType(type)}
                />
                <Label htmlFor={`entity-${type}`} className="cursor-pointer capitalize">
                  {type}
                </Label>
              </div>
            ))}
          </div>
          {localConfig.entity_types.length === 0 && (
            <p className="text-sm text-muted-foreground mt-4">
              No types selected - judge will evaluate all entity types
            </p>
          )}
        </CardContent>
      </Card>

      {/* Matching Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Matching Rules</CardTitle>
          <CardDescription>Configure how facts are compared for equivalence</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Numeric Tolerance */}
          <div className="space-y-2">
            <Label htmlFor="numeric-tolerance">Numeric Tolerance (±%)</Label>
            <Input
              id="numeric-tolerance"
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={localConfig.numeric_tolerance_percent}
              onChange={(e) =>
                updateConfig({ numeric_tolerance_percent: parseFloat(e.target.value) || 0 })
              }
              className="max-w-xs"
            />
            <p className="text-sm text-muted-foreground">
              Numeric values within ±{localConfig.numeric_tolerance_percent}% are considered matching
            </p>
          </div>

          {/* Date Granularity */}
          <div className="space-y-2">
            <Label>Date Granularity</Label>
            <Select
              value={localConfig.date_granularity}
              onValueChange={(value) => updateConfig({ date_granularity: value })}
            >
              <SelectTrigger className="max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="day">Day (exact date match)</SelectItem>
                <SelectItem value="month">Month (ignore day)</SelectItem>
                <SelectItem value="year">Year (ignore month and day)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Boolean Settings */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="case-insensitive"
                checked={localConfig.case_insensitive_strings}
                onCheckedChange={(checked) =>
                  updateConfig({ case_insensitive_strings: checked as boolean })
                }
              />
              <Label htmlFor="case-insensitive" className="cursor-pointer">
                Case-insensitive string comparisons
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="ignore-wording"
                checked={localConfig.ignore_minor_wording_diffs}
                onCheckedChange={(checked) =>
                  updateConfig({ ignore_minor_wording_diffs: checked as boolean })
                }
              />
              <Label htmlFor="ignore-wording" className="cursor-pointer">
                Ignore minor wording differences
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="require-all-fields"
                checked={localConfig.require_all_fields_match}
                onCheckedChange={(checked) =>
                  updateConfig({ require_all_fields_match: checked as boolean })
                }
              />
              <Label htmlFor="require-all-fields" className="cursor-pointer">
                Require all fields to match exactly (strict mode)
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="allow-partial"
                checked={localConfig.allow_partial_matches}
                onCheckedChange={(checked) =>
                  updateConfig({ allow_partial_matches: checked as boolean })
                }
              />
              <Label htmlFor="allow-partial" className="cursor-pointer">
                Allow partial matches to count as correct
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Required Key Fields */}
      <Card>
        <CardHeader>
          <CardTitle>Required Key Fields</CardTitle>
          <CardDescription>
            Specific fields that must match for a fact to be considered correct
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="e.g., account_number, asset_type"
              value={newKeyField}
              onChange={(e) => setNewKeyField(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addKeyField();
                }
              }}
            />
            <Button onClick={addKeyField} variant="outline">
              Add
            </Button>
          </div>
          {localConfig.required_key_fields.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {localConfig.required_key_fields.map((field) => (
                <Badge key={field} variant="secondary" className="px-3 py-1">
                  {field}
                  <button
                    onClick={() => removeKeyField(field)}
                    className="ml-2 hover:text-destructive"
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No required key fields specified</p>
          )}
        </CardContent>
      </Card>

      {/* Extra Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Notes (Optional)</CardTitle>
          <CardDescription>
            Additional instructions for the judge that don't fit into the categories above
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="e.g., Pay special attention to currency conversions, treat 'checking' and 'current' accounts as equivalent..."
            value={localConfig.extra_instructions || ''}
            onChange={(e) =>
              updateConfig({ extra_instructions: e.target.value || null })
            }
            rows={4}
          />
        </CardContent>
      </Card>
    </div>
  );
}
